class AppException(Exception):
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class InvalidCredentialsError(AppException):
    def __init__(self, message: str = "Invalid credentials"):
        super().__init__(message, status_code=401)


class UserNotFoundError(AppException):
    def __init__(self, message: str = "User not found"):
        super().__init__(message, status_code=404)


class UserAlreadyExistsError(AppException):
    def __init__(self, message: str = "User already exists"):
        super().__init__(message, status_code=400)


class ValidationError(AppException):
    def __init__(self, message: str):
        super().__init__(message, status_code=422)


class TokenExpiredError(AppException):
    def __init__(self, message: str = "Token expired"):
        super().__init__(message, status_code=401)


class InvalidTokenError(AppException):
    def __init__(self, message: str = "Invalid token"):
        super().__init__(message, status_code=401)
