import boto3
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer
from config.constants import AWS_REGION, COGNITO_POOL_ID

security = HTTPBearer()

# Initialize AWS Cognito client
cognito_client = boto3.client("cognito-idp", region_name=AWS_REGION)


class AuthenticatedUser:
    def __init__(self, user_details, groups):
        self.user_details = user_details
        self.groups = groups


async def authentication_handler(request: Request):
    headers = request.headers if request.headers else {}
    authorization_token = (
        headers.get("Authorization").split(" ")[1]
        if "Authorization" in headers
        else headers.get("authorization").split(" ")[1]
        if "authorization" in headers
        else None
    )

    if not authorization_token:
        raise HTTPException(status_code=401, detail="Authorization token is missing")

    try:
        # Validate token with Cognito
        user_details = cognito_client.get_user(AccessToken=authorization_token)
        if not user_details:
            raise HTTPException(status_code=401, detail="Invalid token")

        username = user_details["Username"]
        response = cognito_client.admin_list_groups_for_user(
            Username=username, UserPoolId=COGNITO_POOL_ID
        )

        groups = [group["GroupName"] for group in response.get("Groups", [])]

        return AuthenticatedUser(user_details, groups)  # Store in class

    except cognito_client.exceptions.NotAuthorizedException:
        raise HTTPException(status_code=401, detail="Invalid token")
    except cognito_client.exceptions.ExpiredTokenException:
        raise HTTPException(status_code=401, detail="Token expired")
    except Exception as e:
        print("Token validation failed:", str(e))
        raise HTTPException(status_code=500, detail="Token validation failed")


async def get_authenticated_user(
    authenticated_user: AuthenticatedUser = Depends(authentication_handler),
):
    return authenticated_user
