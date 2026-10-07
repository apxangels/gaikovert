import { Link, Route, Routes } from "react-router-dom";
import ScenarioListPage from "./pages/ScenarioListPage";
import ScenarioCreatePage from "./pages/ScenarioCreatePage";
import ScenarioDetailPage from "./pages/ScenarioDetailPage";
import ServiceLibraryPage from "./pages/ServiceLibraryPage";
import MachineLibraryPage from "./pages/MachineLibraryPage";

export default function App() {
  return (
    <div className="app">
      <nav className="navbar">
        <Link to="/">Сценарии</Link>
        <Link to="/library/services">Библиотека сервисов</Link>
        <Link to="/library/machines">Библиотека machine-конфигураций</Link>
      </nav>
      <main>
        <Routes>
          <Route path="/" element={<ScenarioListPage />} />
          <Route path="/scenarios/new" element={<ScenarioCreatePage />} />
          <Route path="/scenarios/:id" element={<ScenarioDetailPage />} />
          <Route path="/library/services" element={<ServiceLibraryPage />} />
          <Route path="/library/machines" element={<MachineLibraryPage />} />
        </Routes>
      </main>
    </div>
  );
}
