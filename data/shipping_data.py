# 오늘 배송할 물량 데이터를 통해, 지역별 MAX 딜리버리를 예측하기 위해, 클러스터 전 전체 물량을 조회하는 로직 필요

class ShippingProcessor:
    def __init__(self, db_handler):
        """Class for processing shipping data"""
        self.db_handler = db_handler

    def fetch_shipping(self, workflow_date):
        """
        Fetches shipping data for a specific date
        workflow_date: 'YYYY-MM-DD' 형식 문자열 (KST 기준)
        """
        query = f"""
            SELECT
                shipping_shippingitem.uuid as shipping_uuid,
                REGEXP_REPLACE(location_sector.code, '[0-9]', '') as Area
            FROM shipping_shippingitem 
            JOIN order_order
                ON shipping_shippingitem.order_id = order_order.id
            JOIN shop_shop 
                ON order_order.shop_id = shop_shop.id
            JOIN location_sector
                ON shipping_shippingitem.designated_sector_id = location_sector.id
            JOIN location_address
                ON shipping_shippingitem.address_id = location_address.id
            JOIN route_pickupbatch
                ON shipping_shippingitem.pickup_batch_id = route_pickupbatch.id
            WHERE shop_shop.id NOT IN (1,3)
            AND DATE_ADD(shipping_shippingitem.timestamp_created, INTERVAL 9 HOUR) >= DATE_ADD(DATE('{workflow_date}'), INTERVAL -3 DAY)
            AND (
                JSON_UNQUOTE(JSON_EXTRACT(order_order.metadata, '$.delivery_date')) IS NULL
                OR JSON_UNQUOTE(JSON_EXTRACT(order_order.metadata, '$.delivery_date')) NOT IN (
                    DATE_FORMAT(
                        DATE_ADD(DATE('{workflow_date}'), INTERVAL 1 DAY),
                        '%Y%m%d'
                    )
                )
            )
            AND shipping_shippingitem.timestamp_delivery_complete IS NULL;
        """
        return self.db_handler.fetch_data("daas", query)