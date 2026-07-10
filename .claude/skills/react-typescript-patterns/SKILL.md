---
name: react-typescript-patterns
description: Write modern React components with TypeScript, proper typing, hooks patterns, and component composition
skills: [react, typescript, hooks]
allowed-tools: [Read, Edit, Write, TaskCreate]
---

# React + TypeScript Patterns Skill

Write type-safe React components using modern hooks and composition patterns.

## Component Typing

### ❌ DON'T (No types or loose typing)
```typescript
export function UserForm({ onSubmit }) {
  const [user, setUser] = useState({});
  return <form>...</form>;
}
```

### ✅ DO (Strict typing)
```typescript
interface UserFormProps {
  onSubmit: (user: UserCreate) => Promise<void>;
  initialUser?: User;
  isLoading?: boolean;
}

interface User {
  id: number;
  email: string;
  name: string;
}

interface UserCreate extends Omit<User, 'id'> {}

export const UserForm: React.FC<UserFormProps> = ({
  onSubmit,
  initialUser,
  isLoading = false
}) => {
  // Implementation
};
```

## State Management with Hooks

```typescript
// app/hooks/useUsers.ts
import { useState, useCallback } from 'react';
import { userApi } from '@/api/users';
import type { User, UserCreate } from '@/types';

interface UseUsersReturn {
  users: User[];
  loading: boolean;
  error: Error | null;
  fetchUsers: () => Promise<void>;
  createUser: (user: UserCreate) => Promise<User>;
  deleteUser: (id: number) => Promise<void>;
}

export const useUsers = (): UseUsersReturn => {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const fetchUsers = useCallback(async () => {
    try {
      setLoading(true);
      const data = await userApi.list();
      setUsers(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Unknown error'));
    } finally {
      setLoading(false);
    }
  }, []);

  const createUser = useCallback(async (userData: UserCreate): Promise<User> => {
    try {
      setLoading(true);
      const newUser = await userApi.create(userData);
      setUsers(prev => [...prev, newUser]);
      return newUser;
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Unknown error'));
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const deleteUser = useCallback(async (id: number) => {
    try {
      await userApi.delete(id);
      setUsers(prev => prev.filter(u => u.id !== id));
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Unknown error'));
      throw err;
    }
  }, []);

  return { users, loading, error, fetchUsers, createUser, deleteUser };
};
```

## API Client with Axios

```typescript
// src/api/client.ts
import axios, { AxiosInstance, AxiosError } from 'axios';

const baseURL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const client: AxiosInstance = axios.create({
  baseURL,
  timeout: 10000,
});

// Request interceptor - add auth token
client.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor - handle errors
client.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      // Handle unauthorized - redirect to login
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// src/api/users.ts
import { client } from './client';
import type { User, UserCreate, UserUpdate } from '@/types';

export const userApi = {
  list: async (): Promise<User[]> => {
    const { data } = await client.get('/api/v1/users');
    return data;
  },

  get: async (id: number): Promise<User> => {
    const { data } = await client.get(`/api/v1/users/${id}`);
    return data;
  },

  create: async (user: UserCreate): Promise<User> => {
    const { data } = await client.post('/api/v1/users', user);
    return data;
  },

  update: async (id: number, user: UserUpdate): Promise<User> => {
    const { data } = await client.patch(`/api/v1/users/${id}`, user);
    return data;
  },

  delete: async (id: number): Promise<void> => {
    await client.delete(`/api/v1/users/${id}`);
  },
};
```

## State Management with Zustand

```typescript
// src/store/userStore.ts
import { create } from 'zustand';
import type { User } from '@/types';

interface UserState {
  currentUser: User | null;
  isAuthenticated: boolean;
  setCurrentUser: (user: User | null) => void;
  logout: () => void;
}

export const useUserStore = create<UserState>((set) => ({
  currentUser: null,
  isAuthenticated: false,

  setCurrentUser: (user) => set({
    currentUser: user,
    isAuthenticated: !!user,
  }),

  logout: () => set({
    currentUser: null,
    isAuthenticated: false,
  }),
}));

// Usage in component
const currentUser = useUserStore(state => state.currentUser);
const logout = useUserStore(state => state.logout);
```

## TanStack Query (React Query)

```typescript
// src/hooks/useUsersQuery.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { userApi } from '@/api/users';
import type { User, UserCreate } from '@/types';

export const useUsersQuery = () => {
  return useQuery({
    queryKey: ['users'],
    queryFn: userApi.list,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
};

export const useUserQuery = (id: number) => {
  return useQuery({
    queryKey: ['users', id],
    queryFn: () => userApi.get(id),
  });
};

export const useCreateUserMutation = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: userApi.create,
    onSuccess: (newUser) => {
      // Update cache
      queryClient.setQueryData<User[]>(['users'], (old) => [
        ...(old || []),
        newUser,
      ]);
    },
  });
};

// Usage in component
const { data: users, isLoading } = useUsersQuery();
const createMutation = useCreateUserMutation();

const handleCreate = async (userData: UserCreate) => {
  await createMutation.mutateAsync(userData);
};
```

## Component Composition

```typescript
// Parent component with data fetching
export const UserList: React.FC = () => {
  const { data: users, isLoading, error } = useUsersQuery();

  if (isLoading) return <LoadingSpinner />;
  if (error) return <ErrorAlert error={error} />;

  return (
    <div>
      <h1>Users</h1>
      {users?.map(user => (
        <UserCard key={user.id} user={user} />
      ))}
    </div>
  );
};

// Presentational component (receives props, doesn't fetch)
interface UserCardProps {
  user: User;
}

export const UserCard: React.FC<UserCardProps> = ({ user }) => {
  return (
    <div className="card">
      <h2>{user.name}</h2>
      <p>{user.email}</p>
    </div>
  );
};
```

## Error Boundaries

```typescript
// src/components/ErrorBoundary.tsx
import React, { ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('Error caught:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        this.props.fallback || (
          <div className="error">
            <h2>Something went wrong</h2>
            <p>{this.state.error?.message}</p>
          </div>
        )
      );
    }

    return this.props.children;
  }
}
```

## Custom Hooks Best Practices

```typescript
// ✅ DO: Return consistent object shape
interface UseFormReturn<T> {
  values: T;
  errors: Record<keyof T, string>;
  touched: Record<keyof T, boolean>;
  handleChange: (name: keyof T, value: unknown) => void;
  handleBlur: (name: keyof T) => void;
  handleSubmit: (onSubmit: (values: T) => void) => (e: React.FormEvent) => void;
  reset: () => void;
}

export const useForm = <T>(initialValues: T): UseFormReturn<T> => {
  const [values, setValues] = React.useState(initialValues);
  const [errors, setErrors] = React.useState<Record<keyof T, string>>({} as Record<keyof T, string>);
  const [touched, setTouched] = React.useState<Record<keyof T, boolean>>({} as Record<keyof T, boolean>);

  // ... implementation

  return { values, errors, touched, handleChange, handleBlur, handleSubmit, reset };
};
```

## TypeScript Configuration

**tsconfig.json**:
```json
{
  "compilerOptions": {
    "target": "ES2020",
    "jsx": "react-jsx",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "paths": {
      "@/*": ["./src/*"]
    }
  }
}
```

## Best Practices Checklist

- ✅ Always type component props with interfaces
- ✅ Use `React.FC<Props>` for functional components
- ✅ Never use `any` - use `unknown` if necessary, then type narrow
- ✅ Extract hooks for reusable logic
- ✅ Keep components small and focused
- ✅ Separate container (data) and presentational components
- ✅ Use composition over inheritance
- ✅ Memoize expensive computations with `useMemo`
- ✅ Memoize callbacks with `useCallback`
- ✅ Avoid prop drilling - use context or state management
