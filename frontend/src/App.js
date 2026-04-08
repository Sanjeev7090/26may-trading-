import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import TradingDashboard from "@/components/TradingDashboard";

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<TradingDashboard />} />
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;
