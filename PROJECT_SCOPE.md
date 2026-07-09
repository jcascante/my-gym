# MyGym - Project Scope & MVP

## Project Vision

A personalized workout program manager that builds custom exercise programs based on user goals, current fitness level, and preferences. Users get day-to-day guidance with progress tracking and adaptive feedback.

## MVP Features

### 1. User Authentication & Onboarding

#### First-Time User Flow
1. **Sign Up** - Email/password registration
2. **Onboarding Form** - Collect:
   - **Personal Info**: Name, age, gender, weight, height
   - **Current Activities**: Type and frequency (sedentary, lightly active, moderately active, very active)
   - **Fitness Focus**: Primary goal (strength, endurance, weight loss, muscle gain, flexibility, general fitness)
   - **Goals**: Short-term (1-3 months), medium-term (3-6 months)
   - **Workout Parameters**:
     - Experience level (beginner, intermediate, advanced)
     - Days per week available for workouts (3-7)
     - Preferred workout duration (30/45/60/90 min)
     - Equipment available (home, gym, bodyweight only)
     - Injuries/limitations to avoid

#### Returning User Flow
1. **Login** - Email/password authentication
2. **Program Dashboard** - View current program
3. **Update Profile** - Option to modify personal info and parameters
4. **Create New Program** - Trigger new program creation with updated preferences

### 2. Program Builder/Engine

#### Program Generation
1. **Input**: User profile data (goals, experience, time available, equipment)
2. **Processing**: 
   - Select appropriate exercises for goals
   - Create progression-based weekly structure
   - Distribute workout days (push/pull/legs, upper/lower, full-body, sport-specific)
   - Account for recovery time
3. **Output**: 
   - Structured workout program (4-12 weeks typical)
   - Daily workout details with exercise progression
   - Form notes and safety tips

#### Program Structure
- **Weekly Schedule**: Daily breakdown of exercises
- **Exercises**: Name, sets, reps, weight/resistance, rest period, form notes
- **Progression**: Week-to-week increases in difficulty
- **Flexibility**: Allow manual adjustments/substitutions

### 3. Program Tracking & Feedback

#### Daily Tracking
1. **Today's Workout**: Display current day's exercises
2. **Logging**: 
   - Mark exercises complete/incomplete
   - Log actual weight/reps performed
   - Rate difficulty (1-10)
   - Note any pain or issues
3. **Feedback**: Quick form (how you felt, energy level, form quality)

#### Progress Insights
1. **Completion Rate**: % of program completed
2. **Performance Trend**: Weight/reps progression over time
3. **Workout Stats**: Total workouts, total volume
4. **Feedback Summary**: Difficulty trends, common issues

#### Adaptive Features
1. **Rest Days**: Suggest adjustments based on fatigue feedback
2. **Progression**: Flag if user is progressing too fast/slow
3. **Alerts**: Notify of form issues or unusual patterns

## Data Models

### Users
```
- id
- email (unique)
- password_hash
- first_name
- last_name
- created_at
- updated_at
```

### User Profile
```
- id
- user_id (foreign key)
- age
- gender
- weight (kg)
- height (cm)
- activity_level (sedentary|lightly_active|moderately_active|very_active)
- fitness_focus (strength|endurance|weight_loss|muscle_gain|flexibility|general)
- experience_level (beginner|intermediate|advanced)
- days_per_week (3-7)
- workout_duration (30|45|60|90)
- equipment (home|gym|bodyweight)
- injuries_limitations (text)
- short_term_goals (text)
- medium_term_goals (text)
- updated_at
```

### Workout Programs
```
- id
- user_id (foreign key)
- name
- description
- status (active|completed|archived)
- start_date
- end_date
- duration_weeks
- focus (same as user.fitness_focus)
- created_at
- updated_at
```

### Workouts (Daily)
```
- id
- program_id (foreign key)
- day_of_week (1-7)
- week_number (1-12)
- name (e.g., "Upper Body Day A")
- description
- exercises (array/relation)
- created_at
```

### Workout Exercises
```
- id
- workout_id (foreign key)
- exercise_id (foreign key)
- order
- sets
- reps_min
- reps_max
- weight_kg (or resistance level)
- rest_seconds
- form_notes
- progression_week (for varying difficulty)
```

### Exercises (Library)
```
- id
- name
- category (push|pull|legs|core|cardio|flexibility)
- muscle_groups (array: chest|back|shoulders|biceps|triceps|forearms|legs|glutes|core|etc)
- equipment_required (bodyweight|dumbbells|barbell|kettlebell|etc)
- difficulty_level (beginner|intermediate|advanced)
- instructions (text)
- form_cues (array)
- safety_notes (text)
```

### User Workout Logs
```
- id
- user_id (foreign key)
- workout_id (foreign key)
- exercise_id (foreign key)
- scheduled_date
- completed_date (null if not done)
- sets_completed
- reps_completed (array per set)
- weight_used (array per set)
- difficulty_rating (1-10)
- pain_or_issues (text)
- completed (boolean)
```

### Workout Feedback
```
- id
- user_id (foreign key)
- workout_id (foreign key)
- logged_date
- energy_level (1-10)
- form_quality (1-10, self-rated)
- general_notes (text)
- created_at
```

## API Endpoints (REST v1)

### Authentication
- `POST /api/v1/auth/signup` - Register new user
- `POST /api/v1/auth/login` - Login user
- `POST /api/v1/auth/refresh` - Refresh token
- `POST /api/v1/auth/logout` - Logout user

### User Profile
- `GET /api/v1/user/profile` - Get user profile
- `PUT /api/v1/user/profile` - Update user profile
- `GET /api/v1/user/programs` - List user programs

### Programs
- `POST /api/v1/programs` - Create new program (trigger builder)
- `GET /api/v1/programs/{id}` - Get program details
- `GET /api/v1/programs/{id}/workouts` - Get all workouts in program
- `PUT /api/v1/programs/{id}` - Update program
- `DELETE /api/v1/programs/{id}` - Archive program

### Workouts
- `GET /api/v1/programs/{program_id}/workouts/{day}` - Get today's workout
- `GET /api/v1/workouts/{id}` - Get workout details with exercises

### Exercise Logs
- `POST /api/v1/workouts/{id}/log` - Log completed workout
- `POST /api/v1/workouts/{id}/exercise/{exercise_id}/log` - Log single exercise
- `GET /api/v1/user/logs` - Get all user logs (for stats)
- `GET /api/v1/user/logs?start_date=X&end_date=Y` - Filtered logs

### Feedback
- `POST /api/v1/workouts/{id}/feedback` - Submit workout feedback
- `GET /api/v1/user/feedback` - Get feedback history

### Exercises (Read-only Library)
- `GET /api/v1/exercises` - List exercises (with filters)
- `GET /api/v1/exercises/{id}` - Get exercise details

## Frontend Pages

### Public Pages
- `/` - Landing page
- `/login` - Login
- `/signup` - Sign up

### Authenticated Pages
- `/dashboard` - Main dashboard
- `/onboarding` - First-time onboarding (if new user)
- `/profile` - User profile (view/edit)
- `/programs` - List of programs
- `/programs/new` - Create new program (builder)
- `/programs/{id}` - View program details
- `/programs/{id}/today` - Today's workout
- `/programs/{id}/progress` - Program progress tracking
- `/analytics` - Progress analytics/stats

## Key Decisions

### Program Builder Approach
**Options:**
1. **Rules-based engine**: Predefined templates/rules → adaptive to user data
2. **Third-party API**: Integration with existing workout program APIs
3. **Hybrid**: Custom templates + external exercise library

**Decision**: Start with **rules-based engine** for MVP
- Define 4-5 program templates (beginner full-body, intermediate push/pull/legs, etc.)
- Template selection based on user profile
- Exercises pulled from local library
- Users can customize later

### Database Strategy
- **Development**: SQLite for quick iteration
- **Production**: PostgreSQL with migrations
- **Seed data**: Exercise library pre-populated via migrations

### Authentication
- JWT tokens (stateless)
- Access token (30-60 min expiry)
- Refresh token (7 days expiry)
- Stored in secure HTTP-only cookies on frontend

## Non-MVP (Future)
- Social features (friends, challenges, leaderboards)
- Advanced analytics (ML-based progress predictions)
- Nutrition tracking
- Video form demonstrations
- Integration with wearables (Fitbit, Apple Watch)
- Mobile app
- Admin dashboard for exercise library management

## Success Metrics (MVP)
- Users can complete onboarding in <5 min
- Program generation <2 sec
- Daily tracking takes <3 min per workout
- >80% of generated programs completed
- User satisfaction >4/5 after first program
