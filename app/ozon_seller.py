import requests
import time
import math
from requests.exceptions import InvalidJSONError
from app import logger

logger = logger.init_logger("ozon_seller")


class OzonSellerClient:
    """Class represents a client to work with Ozon Seller API."""

    def __init__(self, client_id, api_key):
        self.url = "https://api-seller.ozon.ru"
        self.client_id = client_id
        self.api_key = api_key
        self.headers = {"Client-id": self.client_id,
                        "Api-key": self.api_key}

    def get_prices(self):
        """Get product prices from Ozon and send them to db."""
        product_items = self.get_product_items()
        if not product_items:
            return None
        field_names = ["offer_id", "price_index", "volume_weight"]
        price_field_names = ['price', 'old_price', 'premium_price', 'recommended_price',
                             'retail_price', 'vat', 'min_ozon_price', 'marketing_price',
                             'marketing_seller_price']
        commissions_field_names = ['sales_percent', 'fbo_fulfillment_amount', 'fbo_direct_flow_trans_min_amount',
                                   'fbo_direct_flow_trans_max_amount', 'fbo_deliv_to_customer_amount',
                                   'fbo_return_flow_amount', 'fbo_return_flow_trans_min_amount',
                                   'fbo_return_flow_trans_max_amount', 'fbs_first_mile_min_amount',
                                   'fbs_first_mile_max_amount', 'fbs_direct_flow_trans_min_amount',
                                   'fbs_direct_flow_trans_max_amount', 'fbs_deliv_to_customer_amount',
                                   'fbs_return_flow_amount', 'fbs_return_flow_trans_min_amount',
                                   'fbs_return_flow_trans_max_amount']
        # Create dataset to send to db.
        data = []
        for item in product_items:
            product_id = item.get("product_id")
            if product_id is None:
                continue
            row = {"product_id": product_id}
            for name in field_names:
                value = item.get(name)
                if value is not None:
                    if isinstance(value, str):
                        if len(value) > 0:
                            row[name] = value
                    else:
                        row[name] = value

            prices_dict = item.get("price")
            if isinstance(prices_dict, dict):
                for name in price_field_names:
                    value = prices_dict.get(name)
                    if value is not None:
                        if isinstance(value, str):
                            if len(value) > 0:
                                row[name] = value
                        else:
                            row[name] = value

            commissions = item.get("commissions")
            if isinstance(commissions, dict):
                for name in commissions_field_names:
                    value = commissions.get(name)
                    if value is not None:
                        if isinstance(value, str):
                            if len(value) > 0:
                                row[name] = value
                        else:
                            row[name] = value
            row['api_id'] = self.client_id
            row['shop_id'] = 1
            row['date'] = time.strftime('%Y-%m-%d', time.localtime())
            data.append(row)

        self.send_prices_to_db(data)

    def get_product_items(self) -> list[dict]:
        """Returns list of items with product data."""
        request_data = {"filter": {"visibility": "ALL"},
                        "last_id": "",
                        "limit": 500}
        product_items = []
        while True:
            response = None
            try:
                response = requests.post(self.url + "/v4/product/info/prices",
                                         headers=self.headers, json=request_data)
                response.raise_for_status()
                result = response.json()["result"]
                request_data["last_id"] = result.get("last_id")
                items = result.get("items")
                if not items:
                    break
                product_items.extend(items)
            except (UnicodeEncodeError, requests.exceptions.RequestException) as e:
                try:
                    response_data = response.json()
                    logger.error(repr(e) + " " + repr(response_data) + f" Client_id: {self.client_id}.")
                except (AttributeError, InvalidJSONError):
                    logger.error(repr(e) + f" Client_id: {self.client_id}.")
                break
        return product_items

    def send_prices_to_db(self, data):
        """Send data to 'JSON to DB API' to save it in price_table."""
        json_to_db_url = "https://apps1.ecomru.ru:4439/db/price_table"
        # json_to_db_url = "http://127.0.0.1:8000/db/price_table"
        chunk_size = 1000
        parts = math.ceil(len(data) / chunk_size)
        part = 0
        for data_chunk in chunks(data, chunk_size):
            part += 1
            response = None
            try:
                response = requests.post(json_to_db_url, json=data_chunk)
                response.raise_for_status()
                logger.info(f"Data part {part} of {parts} was sent ({len(data_chunk)} items, total: {len(data)})."
                            f" Client_id: {self.client_id}.")
            except requests.exceptions.RequestException as e:
                try:
                    response_data = response.json()
                    logger.error(repr(e) + " " + repr(response_data) + f" Client_id: {self.client_id}.")
                except (AttributeError, InvalidJSONError):
                    logger.error(repr(e) + f" Client_id: {self.client_id}. Data part {part} of {parts}.")


def chunks(sequence, n):
    """Yield successive n-sized chunks from sequence."""
    for i in range(0, len(sequence), n):
        yield sequence[i:i + n]
