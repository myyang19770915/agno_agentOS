import { Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import ChatPage from './pages/ChatPage';
import DatabasePage from './pages/DatabasePage';

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/chat" element={<ChatPage />} />
        <Route path="/database" element={<DatabasePage />} />
        <Route path="*" element={<Navigate to="/chat" replace />} />
      </Route>
    </Routes>
  );
}
