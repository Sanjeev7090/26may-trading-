import requests
import sys
import json
from datetime import datetime

class GannTradingAPITester:
    def __init__(self, base_url="https://device-finder-130.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test(self, name, success, details=""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name} - PASSED")
        else:
            print(f"❌ {name} - FAILED: {details}")
        
        self.test_results.append({
            "test": name,
            "status": "PASSED" if success else "FAILED",
            "details": details
        })

    def run_test(self, name, method, endpoint, expected_status=200, data=None, params=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}" if not endpoint.startswith('http') else endpoint
        headers = {'Content-Type': 'application/json'}
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=30)
            
            success = response.status_code == expected_status
            details = f"Status: {response.status_code}"
            
            if success and response.status_code == 200:
                try:
                    json_data = response.json()
                    if isinstance(json_data, dict):
                        details += f", Keys: {list(json_data.keys())}"
                    elif isinstance(json_data, list):
                        details += f", Items: {len(json_data)}"
                except:
                    details += ", Non-JSON response"
            elif not success:
                try:
                    error_data = response.json()
                    details += f", Error: {error_data.get('detail', 'Unknown error')}"
                except:
                    details += f", Response: {response.text[:100]}"
            
            self.log_test(name, success, details)
            return success, response.json() if success else {}
            
        except Exception as e:
            self.log_test(name, False, f"Exception: {str(e)}")
            return False, {}

    def test_root_endpoint(self):
        """Test /api/ root endpoint"""
        return self.run_test("Root API Endpoint", "GET", "")

    def test_stock_search(self):
        """Test stock search functionality"""
        # Test RELIANCE search
        success1, data1 = self.run_test(
            "Stock Search - RELIANCE", 
            "GET", 
            "stock/search", 
            params={"q": "RELIANCE"}
        )
        
        # Test TCS search
        success2, data2 = self.run_test(
            "Stock Search - TCS", 
            "GET", 
            "stock/search", 
            params={"q": "TCS"}
        )
        
        # Validate search results
        if success1 and data1.get('results'):
            reliance_found = any('RELIANCE' in result.get('ticker', '') for result in data1['results'])
            self.log_test("RELIANCE Found in Results", reliance_found, 
                         f"Found {len(data1['results'])} results")
        
        if success2 and data2.get('results'):
            tcs_found = any('TCS' in result.get('ticker', '') for result in data2['results'])
            self.log_test("TCS Found in Results", tcs_found, 
                         f"Found {len(data2['results'])} results")
        
        return success1 and success2

    def test_stock_bars(self):
        """Test stock OHLCV data retrieval"""
        # Test TCS.NS bars
        success1, data1 = self.run_test(
            "Stock Bars - TCS.NS", 
            "GET", 
            "stock/bars/TCS.NS"
        )
        
        # Test RELIANCE.NS bars
        success2, data2 = self.run_test(
            "Stock Bars - RELIANCE.NS", 
            "GET", 
            "stock/bars/RELIANCE.NS"
        )
        
        # Validate bars data structure
        if success1 and data1.get('bars'):
            bars = data1['bars']
            if len(bars) > 0:
                bar = bars[0]
                required_fields = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
                has_all_fields = all(field in bar for field in required_fields)
                self.log_test("TCS Bars Data Structure", has_all_fields, 
                             f"Bars count: {len(bars)}, Fields: {list(bar.keys())}")
        
        return success1 and success2

    def test_ai_analysis(self):
        """Test AI trade analysis"""
        # First get some stock data
        success, stock_data = self.run_test(
            "Get Stock Data for AI Analysis", 
            "GET", 
            "stock/bars/TCS.NS",
            params={"limit": 60}
        )
        
        if not success or not stock_data.get('bars'):
            self.log_test("AI Analysis - No Stock Data", False, "Cannot test without stock data")
            return False
        
        # Prepare AI analysis request
        bars = stock_data['bars'][-60:]  # Last 60 bars
        ai_request = {
            "ticker": "TCS.NS",
            "timeframe": "1D",
            "bars": bars
        }
        
        return self.run_test(
            "AI Trade Analysis", 
            "POST", 
            "ai/analyze-chart", 
            data=ai_request
        )[0]

    def test_falling_knife_analysis(self):
        """Test Falling Knife analysis"""
        # Get stock data first
        success, stock_data = self.run_test(
            "Get Stock Data for Falling Knife", 
            "GET", 
            "stock/bars/TCS.NS",
            params={"limit": 60}
        )
        
        if not success or not stock_data.get('bars'):
            return False
        
        falling_knife_request = {
            "ticker": "TCS.NS",
            "bars": stock_data['bars']
        }
        
        return self.run_test(
            "Falling Knife Analysis", 
            "POST", 
            "falling-knife/analyze", 
            data=falling_knife_request
        )[0]

    def test_reverse_swings_analysis(self):
        """Test Reverse Price Swings analysis"""
        # Get stock data first
        success, stock_data = self.run_test(
            "Get Stock Data for Reverse Swings", 
            "GET", 
            "stock/bars/TCS.NS",
            params={"limit": 30}
        )
        
        if not success or not stock_data.get('bars'):
            return False
        
        # Test Method A
        reverse_swings_request = {
            "ticker": "TCS.NS",
            "bars": stock_data['bars'],
            "force_method": "A"
        }
        
        success_a = self.run_test(
            "Reverse Swings - Method A", 
            "POST", 
            "reverse-swings/analyze", 
            data=reverse_swings_request
        )[0]
        
        # Test Method B
        reverse_swings_request["force_method"] = "B"
        success_b = self.run_test(
            "Reverse Swings - Method B", 
            "POST", 
            "reverse-swings/analyze", 
            data=reverse_swings_request
        )[0]
        
        return success_a and success_b

    def test_explosive_volume_analysis(self):
        """Test Explosive Volume analysis"""
        # Get stock data first
        success, stock_data = self.run_test(
            "Get Stock Data for Explosive Volume", 
            "GET", 
            "stock/bars/TCS.NS",
            params={"limit": 60}
        )
        
        if not success or not stock_data.get('bars'):
            return False
        
        explosive_volume_request = {
            "ticker": "TCS.NS",
            "bars": stock_data['bars']
        }
        
        return self.run_test(
            "Explosive Volume Analysis", 
            "POST", 
            "explosive-volume/analyze", 
            data=explosive_volume_request
        )[0]

    def test_golden_setup_analysis(self):
        """Test Golden Setup analysis"""
        # Get stock data first
        success, stock_data = self.run_test(
            "Get Stock Data for Golden Setup", 
            "GET", 
            "stock/bars/TCS.NS",
            params={"limit": 60}
        )
        
        if not success or not stock_data.get('bars'):
            return False
        
        # Test Normal Mode
        golden_setup_request = {
            "ticker": "TCS.NS",
            "bars": stock_data['bars'],
            "pro_mode": False
        }
        
        success_normal = self.run_test(
            "Golden Setup - Normal Mode", 
            "POST", 
            "golden-setup/analyze", 
            data=golden_setup_request
        )[0]
        
        # Test Pro Mode
        golden_setup_request["pro_mode"] = True
        success_pro = self.run_test(
            "Golden Setup - Pro Mode", 
            "POST", 
            "golden-setup/analyze", 
            data=golden_setup_request
        )[0]
        
        return success_normal and success_pro

    def test_ghost_mode_scanner(self):
        """Test Ghost Mode scanner"""
        return self.run_test(
            "Ghost Mode Scanner", 
            "GET", 
            "ghost/scan",
            params={"min_match": 3}
        )[0]

    def test_square_of_9(self):
        """Test Square of 9 calculator"""
        return self.run_test(
            "Square of 9 Calculator", 
            "GET", 
            "square-of-9",
            params={"center_price": 3500.0}
        )[0]

    def test_gann_fan(self):
        """Test Gann Fan calculation"""
        gann_request = {
            "ticker": "TCS.NS",
            "pivot_price": 3500.0,
            "pivot_timestamp": int(datetime.now().timestamp() * 1000),
            "bars_count": 50
        }
        
        return self.run_test(
            "Gann Fan Calculation", 
            "POST", 
            "gann/fan", 
            data=gann_request
        )[0]

    def test_signal_generation(self):
        """Test signal generation"""
        return self.run_test(
            "Signal Generation", 
            "GET", 
            "signal/TCS.NS",
            params={
                "pivot_price": 3500.0,
                "pivot_timestamp": int(datetime.now().timestamp() * 1000)
            }
        )[0]

    def run_all_tests(self):
        """Run all backend API tests"""
        print(f"🚀 Starting Gann Trading API Tests")
        print(f"📡 Testing endpoint: {self.base_url}")
        print("=" * 60)
        
        # Core API tests
        self.test_root_endpoint()
        self.test_stock_search()
        self.test_stock_bars()
        
        # Analysis tests
        self.test_ai_analysis()
        self.test_falling_knife_analysis()
        self.test_reverse_swings_analysis()
        self.test_explosive_volume_analysis()
        self.test_golden_setup_analysis()
        
        # Utility tests
        self.test_square_of_9()
        self.test_gann_fan()
        self.test_signal_generation()
        
        # Ghost mode (may take longer)
        print("\n⚠️  Testing Ghost Mode Scanner (may take 1-2 minutes)...")
        self.test_ghost_mode_scanner()
        
        # Print summary
        print("\n" + "=" * 60)
        print(f"📊 Test Summary: {self.tests_passed}/{self.tests_run} tests passed")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All tests PASSED!")
            return 0
        else:
            print(f"⚠️  {self.tests_run - self.tests_passed} tests FAILED")
            return 1

def main():
    tester = GannTradingAPITester()
    return tester.run_all_tests()

if __name__ == "__main__":
    sys.exit(main())