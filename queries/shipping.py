# shipping_processor.py
class ShippingDatasetQuery:
    def __init__(self, db_handler):
        self.db_handler = db_handler

    def fetch_dataset_df(self):
        query = r"""
            SELECT
                shipping_shippingitem.uuid,
                REGEXP_REPLACE(location_sector.code, '[0-9]', '') as Area
            FROM shipping_shippingitem 
            LEFT JOIN order_order
            ON shipping_shippingitem.order_id = order_order.id
            LEFT JOIN shop_shop 
            ON order_order.shop_id = shop_shop.id
            LEFT JOIN location_sector
            ON shipping_shippingitem.designated_sector_id = location_sector.id
            left JOIN location_address
            on shipping_shippingitem.address_id = location_address.id
            left join route_pickupbatch
            on shipping_shippingitem.pickup_batch_id = route_pickupbatch.id
            JOIN shipping_shippingitemtimetable st
            ON shipping_shippingitem.id = st.shipping_item_id
            WHERE shop_shop.id not iN (1,3)
            AND DATE_ADD(st.timestamp_created, INTERVAL 9 HOUR) >= DATE_ADD(DATE_ADD(NOW(), INTERVAL 9 HOUR), INTERVAL -3 day)
            AND (
                JSON_UNQUOTE(JSON_EXTRACT(order_order.metadata, '$.delivery_date')) IS NULL
                OR JSON_UNQUOTE(JSON_EXTRACT(order_order.metadata, '$.delivery_date')) NOT IN (
                    DATE_FORMAT(
                        DATE_ADD(CONVERT_TZ(NOW(), '+00:00', '+09:00'), INTERVAL 1 DAY),
                        '%Y%m%d'
                    )
                    )
            )
            AND st.timestamp_delivery_complete IS NULL
        """
        return self.db_handler.fetch_data("daas", query)
