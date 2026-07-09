# Login & Sign-Up Technical Documentation

## Overview

MyGym is a personalized workout program manager built with FastAPI (backend), React (frontend), and PostgreSQL (database). The login and sign-up feature implements JWT-based authentication with secure password hashing, providing user account management and session handling.

## Architecture

### Authentication Flow

```
Sign-Up                          Login
   |                              |
   v                              v
POST /api/v1/auth/signup   POST /api/v1/auth/login
   |                              |
   +---> Hash Password            +---> Verify Password
   |     (SHA256 + bcrypt)         |     (SHA256 + bcrypt)
   |                              |
   +---> Create User              +---> Validate Credentials
   |     (DB insert)              |
   |                              |
   +---> Generate Tokens          +---> Generate Tokens
   |     (Access + Refresh)       |     (Access + Refresh)
   |                              |
   v                              v
Set HTTP-Only Cookies        Set HTTP-Only Cookies
Redirect to Onboarding       Redirect to Dashboard
```

### Security Mechanisms

1. **Password Hashing**: SHA-256 pre-hashing for passwords > 72 bytes, then bcrypt
2. **JWT Tokens**: Access tokens (15 min) + Refresh tokens (7 days)
3. **HTTP-Only Cookies**: Secure token storage, prevents XSS attacks
4. **Token Rotation**: Refresh token rotation on each use
5. **CORS**: Cross-origin requests validated against allowed origins

## Backend Implementation

### Models

#### User Model
Location: `backend/app/models/user.py`

```python
class User(Base):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str | None] = mapped_column(String(100))
    hashed_password: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)
```

### Schemas

Location: `backend/app/schemas/user.py`

- `UserSignUpRequest`: Email, password, first_name, last_name
- `UserLoginRequest`: Email, password
- `UserResponse`: User data (without password)
- `TokenResponse`: Access token, refresh token, token type

### API Endpoints

#### Sign-Up
```
POST /api/v1/auth/signup
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "secure_password_123",
  "first_name": "John",
  "last_name": "Doe"
}

Response (201 Created):
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer"
}
```

**Validation**:
- Email must be unique and valid email format
- Password must be at least 8 characters
- First name required, last name optional

**Error Responses**:
- `400 Bad Request`: Invalid email, password too short, email already exists
- `500 Internal Server Error`: Database error

#### Login
```
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "secure_password_123"
}

Response (200 OK):
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer"
}
```

**Validation**:
- Email must exist in database
- Password must match hashed password in database

**Error Responses**:
- `401 Unauthorized`: Invalid email or password
- `400 Bad Request`: Missing required fields

#### Logout
```
POST /api/v1/auth/logout

Response (200 OK):
{
  "message": "Successfully logged out"
}
```

**Note**: Logout is primarily for client-side cleanup. Tokens expire naturally after their TTL.

#### Refresh Token
```
POST /api/v1/auth/refresh
Cookie: refresh_token=...

Response (200 OK):
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer"
}
```

**Implementation**: `backend/app/api/v1/endpoints/auth.py`

### Security Module

Location: `backend/app/core/security.py`

#### Password Hashing
```python
def hash_password(password: str) -> str:
    # SHA-256 pre-hashing for passwords > 72 bytes (bcrypt limitation)
    if len(password.encode()) > 72:
        password = hashlib.sha256(password.encode()).hexdigest()
    return pwd_context.hash(password)  # bcrypt with 12 rounds
```

**Why SHA-256 pre-hashing?**
- Bcrypt has a 72-byte password limit
- Pre-hashing converts any length password to 64-character hex string
- No security loss: bcrypt still hashes the SHA-256 result
- Maintains backward compatibility with older systems

#### Password Verification
```python
def verify_password(plain_password: str, hashed_password: str) -> bool:
    # Apply same pre-hashing for consistency
    if len(plain_password.encode()) > 72:
        plain_password = hashlib.sha256(plain_password.encode()).hexdigest()
    return pwd_context.verify(plain_password, hashed_password)
```

#### JWT Token Creation
```python
def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")

def create_refresh_token(data: dict[str, Any]) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=7)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
```

### Dependencies

Location: `backend/app/core/dependencies.py`

```python
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session)
) -> User:
    # Decode JWT token
    payload = decode_token(token)
    user_id = payload.get("sub")
    
    # Fetch user from database
    user = await session.get(User, int(user_id))
    
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    return user
```

Used in protected routes:
```python
@router.get("/me")
async def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    return UserResponse.from_orm(current_user)
```

### Configuration

Location: `backend/app/core/config.py`

```python
class Settings(BaseSettings):
    # JWT
    SECRET_KEY: str  # Used for token signing
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Database
    DATABASE_URL: str
    
    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]
```

## Frontend Implementation

### Components

#### LoginPage
Location: `frontend/src/pages/LoginPage.tsx`

- Email input with validation
- Password input (masked)
- Form submission to `/api/v1/auth/login`
- Error handling and display
- Link to sign-up page

#### SignUpPage
Location: `frontend/src/pages/SignUpPage.tsx`

- Email input with validation
- Password input (masked)
- Confirm password validation
- First name and last name inputs
- Form submission to `/api/v1/auth/signup`
- Error handling and display
- Link to login page

#### DashboardPage
Location: `frontend/src/pages/DashboardPage.tsx`

- Logout button (top-right)
- Displays current user's first name
- Protected route (redirects to login if not authenticated)

### API Client

Location: `frontend/src/api/auth.ts`

```typescript
// Sign up new user
async function signup(data: SignUpRequest): Promise<TokenResponse> {
  const response = await fetch('/api/v1/auth/signup', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
    credentials: 'include'  // Include cookies
  })
  return response.json()
}

// Login existing user
async function login(data: LoginRequest): Promise<TokenResponse> {
  const response = await fetch('/api/v1/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
    credentials: 'include'
  })
  return response.json()
}

// Logout
async function logout(): Promise<void> {
  await fetch('/api/v1/auth/logout', {
    method: 'POST',
    credentials: 'include'
  })
}

// Clear auth tokens from storage
function clearAuthToken(): void {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
}
```

### State Management

Location: `frontend/src/store/auth.ts`

Uses Zustand for auth state:
```typescript
const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: false,
  
  setUser: (user) => set({ user, isAuthenticated: !!user }),
  clearAuth: () => set({ user: null, isAuthenticated: false }),
  
  // Load user from API on app init
  loadUser: async () => {
    const response = await fetch('/api/v1/auth/me')
    if (response.ok) {
      const user = await response.json()
      set({ user, isAuthenticated: true })
    }
  }
}))
```

### Routing

Location: `frontend/src/main.tsx`

Protected routes check authentication before rendering:
```typescript
function ProtectedRoute({ children }) {
  const { isAuthenticated } = useAuthStore()
  
  if (!isAuthenticated) {
    return <Navigate to="/login" />
  }
  
  return children
}
```

## Data Flow

### Sign-Up Flow
1. User submits email, password, name via SignUpPage
2. Frontend validates input locally
3. Frontend POSTs to `/api/v1/auth/signup`
4. Backend:
   - Validates email uniqueness
   - Hashes password (SHA-256 + bcrypt)
   - Creates User record in DB
   - Generates JWT tokens
   - Sets HTTP-only cookies
5. Frontend receives tokens
6. Frontend stores in Zustand store
7. Frontend redirects to onboarding
8. Subsequent requests include JWT in Authorization header

### Login Flow
1. User submits email & password via LoginPage
2. Frontend validates input locally
3. Frontend POSTs to `/api/v1/auth/login`
4. Backend:
   - Looks up user by email
   - Verifies password (SHA-256 + bcrypt)
   - Generates new JWT tokens
   - Sets HTTP-only cookies
5. Frontend stores tokens and user data
6. Frontend redirects to dashboard
7. API requests include JWT (via cookie or Authorization header)

### Logout Flow
1. User clicks logout button on DashboardPage
2. Frontend calls POST `/api/v1/auth/logout`
3. Backend invalidates session (optional)
4. Frontend clears local tokens
5. Frontend clears Zustand auth state
6. Frontend redirects to login page

## Testing

### Backend Tests
Location: `backend/tests/test_auth.py`

```bash
pytest backend/tests/test_auth.py -v
```

Tests cover:
- User creation with valid/invalid data
- Password hashing and verification
- JWT token creation and validation
- Login with correct/incorrect credentials
- Protected endpoint access
- Token refresh

### Frontend Tests
Location: `frontend/src/tests/`

Tests cover:
- Login form submission
- Sign-up form validation
- Error message display
- Navigation after auth
- Logout functionality

## Deployment Considerations

1. **Environment Variables**
   - Set `SECRET_KEY` to a strong random string
   - Configure `DATABASE_URL` for production database
   - Update `CORS_ORIGINS` for production domain

2. **Security Headers**
   - Set `Secure` flag on cookies in HTTPS
   - Set `SameSite=Strict` for CSRF protection
   - Use HSTS headers

3. **Rate Limiting**
   - Consider rate limiting login attempts
   - Implement CAPTCHA for suspicious activity

4. **Monitoring**
   - Log failed login attempts
   - Monitor for brute force attacks
   - Track unusual access patterns

## Troubleshooting

### Common Issues

**"Password cannot be longer than 72 bytes"**
- Fixed by SHA-256 pre-hashing in `hash_password()` and `verify_password()`
- Applies to passwords > 72 bytes

**"Invalid credentials" with correct password**
- Check password was hashed with current algorithm
- Verify bcrypt version is compatible with passlib (bcrypt < 5.0.0)

**Tokens not persisted across requests**
- Ensure `credentials: 'include'` in fetch options
- Check CORS allows credentials
- Verify cookies are set with HTTP-only flag

**User not authenticated after login**
- Check token is valid and not expired
- Verify `get_current_user()` dependency is used
- Check database session is active

## References

- [JWT.io](https://jwt.io) - JWT standard
- [bcrypt](https://en.wikipedia.org/wiki/Bcrypt) - Password hashing
- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
