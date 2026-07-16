import { Link } from 'react-router-dom';
import { Button } from '@/components';

export default function ProgramsListPage() {
  // MVP: link to the builder; a GET /user/programs list endpoint can populate this later.
  return (
    <div className="max-w-2xl mx-auto p-4">
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-2xl font-bold">Your programs</h1>
        <Link to="/programs/new">
          <Button>Create program</Button>
        </Link>
      </div>
      <p className="text-gray-500">Create your first program to get started.</p>
    </div>
  );
}
