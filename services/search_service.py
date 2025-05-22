from connection.postgres import close_connection, get_db_engine, load_all_tables
from connection.milvus import create_or_load_db, create_or_load_collection
from helpers.service import print_log
from request_types.search import SearchKnowledgeBaseRequest
from llama_index.core import Settings
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding
from sqlalchemy import func
from sqlalchemy import and_
from config.constants import (
    OPEN_API_KEY,
    MILVUS_DATABASE_NAME,
    MILVUS_CONTENT_COLLECTION_NAME,
    LLM_MODEL_NAME,
    EMBEDDING_MODEL_NAME,
    TOPICS_TABLE_NAME,
    USER_CHAT_HISTORY_TABLE_NAME,
    USER_CONVERSATION_TABLE_NAME,
    CHAT_HISTORY_SIZE,
)
from helpers.prompts import search_prompt, conversation_title_prompt
from fastapi import HTTPException, status

metadataCollection = load_all_tables()
Settings.llm = OpenAI(model=LLM_MODEL_NAME, temperature=0.7, api_key=OPEN_API_KEY)


def generate_conversation_title(question: str):
    try:
        question_prompt = conversation_title_prompt(question=question)
        response = Settings.llm.complete(question_prompt)

        return response.text.strip()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


def generate_llm_response(user_query, context_texts, chat_history_data):
    # Initialize LlamaIndex with OpenAI GPT-3.5 Turbo
    try:
        prompt_template = search_prompt(
            user_query=user_query,
            context_texts=context_texts,
            chat_history_data=chat_history_data,
        )

        response = Settings.llm.complete(prompt_template)

        return response.text.strip()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


def generate_embedding(text: str):
    embed_model = OpenAIEmbedding(model_name=EMBEDDING_MODEL_NAME, api_key=OPEN_API_KEY)
    return embed_model.get_text_embedding(text)


def search_knowledge_base(request: SearchKnowledgeBaseRequest):
    db, engine = None, None
    try:
        print_log("search_knowledge_base", "POST", "entry", request)
        db, engine = get_db_engine()
        """Get old chat history with the conversation"""
        user_conversation_table = metadataCollection.tables[
            USER_CONVERSATION_TABLE_NAME
        ]
        user_chat_history_table = metadataCollection.tables[
            USER_CHAT_HISTORY_TABLE_NAME
        ]

        """Create conversation if it's first time"""
        conversation_id = None
        chat_history_data = []
        conversation_title = generate_conversation_title(question=request.search_key)
        if not request.con_id:
            result = db.execute(
                user_conversation_table.insert()
                .values(
                    {
                        "username": request.username,
                        "name": conversation_title or request.search_key,
                        "updated_at": func.now(),
                    }
                )
                .returning(user_conversation_table.c.id)
            ).scalar()
            db.commit()

            conversation_id = str(result)
            chat_history_data = []
        elif request.con_id:
            conversation_id = request.con_id
            chat_history_data = (
                db.execute(
                    user_chat_history_table.select()
                    .with_only_columns(
                        user_chat_history_table.c.question,
                        user_chat_history_table.c.answer,
                    )
                    .where(
                        user_chat_history_table.c.conversation_id == conversation_id,
                        user_chat_history_table.c.is_deleted == False,
                    )
                    .order_by(user_chat_history_table.c.created_at.desc())
                    .limit(CHAT_HISTORY_SIZE)
                )
                .mappings()
                .fetchall()
            )

        if chat_history_data:
            chat_history_data = chat_history_data[::-1]
        elif not chat_history_data:
            chat_history_data = []

        context_texts = []
        response = generate_llm_response(
            user_query=request.search_key,
            context_texts=context_texts,
            chat_history_data=[],
        )

        """If the response is a greeting or feedback, return it immediately (no need for Milvus search)"""
        if response.lower().startswith(
            ("hello", "hi", "hey", "you're welcome", "thank you", "thank", "thanks")
        ):
            request_data_for_search = {
                "question": request.search_key,
                "answer": response,
                "model_name": LLM_MODEL_NAME,
                "topic_id": request.topic_id,
                "conversation_id": conversation_id,
                "is_deleted": False,
                "updated_at": func.now(),
            }

            print("request_data_for_search::::", request_data_for_search)
            db.execute(user_chat_history_table.insert().values(request_data_for_search))
            db.commit()
            return {"data": response, "conversation_id": conversation_id, "error": None}

        """Milvus connection"""
        create_or_load_db(MILVUS_DATABASE_NAME)
        collection = create_or_load_collection(MILVUS_CONTENT_COLLECTION_NAME)

        """Query embedding"""
        query_embedding = generate_embedding(request.search_key)

        """search in milvus"""
        index_params = {
            "index_type": "IVF_FLAT",
            "metric_type": "L2",
            "params": {"nlist": 128},
        }

        collection.create_index(field_name="embedding", index_params=index_params)
        collection.load()

        search_params = {"metric_type": "L2", "params": {"nprobe": 10}}

        delete_condition = "is_deleted == false"
        expr_condition = delete_condition
        topic_id_condition = ""

        if request.topic_id:
            """For Specific Topic Search"""
            topic_id_condition = f"ARRAY_CONTAINS(topic_ids, {int(request.topic_id)})"
        elif not any([request.topic_id, request.l2, request.l3]):
            """For Global Search"""
            topics_table = metadataCollection.tables[TOPICS_TABLE_NAME]
            query_check = (
                topics_table.select()
                .with_only_columns(topics_table.c.id)
                .where(topics_table.c.is_deleted == False)
            ).where(
                and_(
                    topics_table.c.tenant.in_(["ALL"]),
                    topics_table.c.facility.in_(["ALL"]),
                )
            )
            result = db.execute(query_check).mappings().fetchall()
            if result:
                topic_ids_data = [int(obj.id) for obj in result]
                if topic_ids_data:
                    topic_id_condition = " OR ".join(
                        [
                            f"ARRAY_CONTAINS(topic_ids, {int(topic_id)})"
                            for topic_id in topic_ids_data
                        ]
                    )

        elif request.l2 or request.l3:
            """Level Management search"""
            topics_table = metadataCollection.tables[TOPICS_TABLE_NAME]
            l2_list = [t.strip() for t in request.l2.split(",")] if request.l2 else []
            l3_list = [t.strip() for t in request.l3.split(",")] if request.l3 else []

            query_check = (
                topics_table.select()
                .with_only_columns(topics_table.c.id)
                .where(topics_table.c.is_deleted == False)
            )
            if l3_list:
                """If l3 is provided, strict match both tenant and facility"""
                query_check = query_check.where(
                    and_(
                        topics_table.c.tenant.in_(l2_list),
                        topics_table.c.facility.in_(l3_list),
                    )
                )
            else:
                """If only l2 is provided, match only tenant"""
                query_check = query_check.where(topics_table.c.tenant.in_(l2_list))

            result = db.execute(query_check).mappings().fetchall()
            if result:
                topic_ids_data = [int(obj.id) for obj in result]
                if topic_ids_data:
                    topic_id_condition = " OR ".join(
                        [
                            f"ARRAY_CONTAINS(topic_ids, {int(topic_id)})"
                            for topic_id in topic_ids_data
                        ]
                    )

        """Combine conditions if topic_id is provided"""
        if topic_id_condition:
            expr_condition = f"({topic_id_condition}) and ({delete_condition})"

        """Search Relvant documents in Milvus"""
        results = collection.search(
            data=[query_embedding],
            anns_field="embedding",
            param=search_params,
            limit=3,
            output_fields=["text", "topic_ids"],
            expr=expr_condition,
        )

        matches = []
        """relavant article search filter"""
        for result in results[0]:
            if result.distance < 0.5:
                matches.append({"text": result.entity.text})

        if not matches and not chat_history_data:
            request_data_for_search_2 = {
                "question": request.search_key,
                "answer": "No relevant information found.",
                "model_name": LLM_MODEL_NAME,
                "topic_id": request.topic_id,
                "conversation_id": conversation_id,
                "is_deleted": False,
                "updated_at": func.now(),
            }

            print("request_data_for_search_2::::", request_data_for_search_2)
            db.execute(
                user_chat_history_table.insert().values(request_data_for_search_2)
            )
            db.commit()
            return {
                "data": "No relevant information found.",
                "conversation_id": conversation_id,
                "error": None,
            }

        context_texts = [res["text"] for res in matches]

        """generate llm response based on question and context"""
        response = generate_llm_response(
            user_query=request.search_key,
            context_texts=context_texts,
            chat_history_data=chat_history_data,
        )

        """Save user chat history"""
        request_data_for_search_3 = {
            "question": request.search_key,
            "answer": response,
            "model_name": LLM_MODEL_NAME,
            "topic_id": request.topic_id,
            "conversation_id": str(conversation_id),
            "is_deleted": False,
            "updated_at": func.now(),
        }

        print("request_data_for_search_3::::", request_data_for_search_3)
        db.execute(user_chat_history_table.insert().values(request_data_for_search_3))
        db.commit()

        print_log("search_knowledge_base", "POST", "exit", "search successfull")
        return {
            "data": response,
            "conversation_id": conversation_id,
            "error": None,
        }
    except Exception as e:
        print_log(
            "search_knowledge_base",
            "POST",
            "error",
            f"Error occurred while searching knowledge base: {e}",
        )
        if db:
            db.rollback()
        close_connection(db, engine)
        return {"data": None, "conversation_id": None, "error": str(e)}
