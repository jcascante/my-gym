class AppException(Exception):
    error_code: str = "APP_ERROR"

    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class InvalidCredentialsError(AppException):
    error_code: str = "INVALID_CREDENTIALS"

    def __init__(self, message: str = "Invalid credentials"):
        super().__init__(message, status_code=401)


class UserNotFoundError(AppException):
    error_code: str = "USER_NOT_FOUND"

    def __init__(self, message: str = "User not found"):
        super().__init__(message, status_code=404)


class UserAlreadyExistsError(AppException):
    error_code: str = "USER_ALREADY_EXISTS"

    def __init__(self, message: str = "User already exists"):
        super().__init__(message, status_code=400)


class TrainingEnvironmentNotFoundError(AppException):
    error_code: str = "TRAINING_ENVIRONMENT_NOT_FOUND"

    def __init__(self, message: str = "Training environment not found"):
        super().__init__(message, status_code=404)


class InjuryRecordNotFoundError(AppException):
    error_code: str = "INJURY_RECORD_NOT_FOUND"

    def __init__(self, message: str = "Injury record not found"):
        super().__init__(message, status_code=404)


class ExerciseNotFoundError(AppException):
    error_code: str = "EXERCISE_NOT_FOUND"

    def __init__(self, message: str = "Exercise not found"):
        super().__init__(message, status_code=404)


class ValidationError(AppException):
    error_code: str = "VALIDATION_ERROR"

    def __init__(self, message: str):
        super().__init__(message, status_code=422)


class TokenExpiredError(AppException):
    error_code: str = "TOKEN_EXPIRED"

    def __init__(self, message: str = "Token expired"):
        super().__init__(message, status_code=401)


class InvalidTokenError(AppException):
    error_code: str = "INVALID_TOKEN"

    def __init__(self, message: str = "Invalid token"):
        super().__init__(message, status_code=401)


class ProgramTemplateNotFoundError(AppException):
    error_code: str = "PROGRAM_TEMPLATE_NOT_FOUND"

    def __init__(self, message: str = "Program template not found"):
        super().__init__(message, status_code=404)


class ProgramNotFoundError(AppException):
    error_code: str = "PROGRAM_NOT_FOUND"

    def __init__(self, message: str = "Program not found"):
        super().__init__(message, status_code=404)


class WorkoutExerciseNotFoundError(AppException):
    error_code: str = "WORKOUT_EXERCISE_NOT_FOUND"

    def __init__(self, message: str = "Workout exercise not found"):
        super().__init__(message, status_code=404)
