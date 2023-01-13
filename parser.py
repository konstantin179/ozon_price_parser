import requests
import app.database as db
from app.database import engine
from app.ozon_seller import OzonSellerClient
from concurrent.futures import ThreadPoolExecutor
from app import logger


logger = logger.init_logger("parser")


def save_ozon_prices(creds):
    client_id = creds[0]
    api_key = creds[1]
    client = OzonSellerClient(client_id, api_key)
    client.get_prices()
    # prod_items = client.get_product_items()
    # marketing_actions = []
    # for item in prod_items:
    #     marketing_actions.append(item.get('marketing_actions'))
    # for i in marketing_actions:
    #     print(i)


def delete_duplicates_from_price_table():
    url = "https://apps1.ecomru.ru:4439/db/price_table/delete_duplicates"
    # url = "http://127.0.0.1:8000/db/price_table/delete_duplicates"
    try:
        response = requests.delete(url)
        response.raise_for_status()
        logger.info("Duplicates were deleted from price_table")
    except requests.exceptions.RequestException as e:
        logger.error(repr(e))


def update_accounts_prices(client_id: str | int | list[int] = 'all'):
    accounts_data = db.get_accounts_data(engine, client_id=client_id)
    credentials = []
    for acc_data in accounts_data.values():
        credentials.append((acc_data['client_id'], acc_data['api_key']))

    # print(credentials)
    # print(len(credentials))

    logger.info(f"Start parsing data for clients: {client_id}")
    # # One-thread
    # for cred in credentials:
    #     save_ozon_prices(cred)

    # Multi-thread
    with ThreadPoolExecutor() as executor:
        executor.map(save_ozon_prices, credentials)
    logger.info("End of parsing")

    delete_duplicates_from_price_table()


if __name__ == '__main__':
    update_accounts_prices()
