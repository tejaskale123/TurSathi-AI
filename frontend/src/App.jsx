import { Routes, Route } from 'react-router-dom';
import Splash from './pages/Splash/Splash';
import Login from './pages/Login/Login';
import Register from './pages/Register/Register';

function App() {
  return (
    <Routes>
      <Route path="/" element={<Splash />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="*" element={<Splash />} />
    </Routes>
  );
}

export default App;
