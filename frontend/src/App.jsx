import { useAuth } from "./context/AuthContext";
import LoginForm from "./components/LoginForm";
import DeskPage from "./pages/DeskPage";

export default function App() {
  const { user, loading } = useAuth();

  if (loading) return null;
  return user ? <DeskPage /> : <LoginForm />;
}
