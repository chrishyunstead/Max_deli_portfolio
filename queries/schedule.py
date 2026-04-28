# schedule_processor.py
class ScheduleDatasetQuery:
    def __init__(self, db_handler):
        self.db_handler = db_handler

    def fetch_dataset_df(self):
        query = r"""
            SELECT
                dispatch_dataset.requested_date as 'Date',
                dispatch_dataset.bunny_color as 'Type',
                location_sector.code as 'code',
                dispatch_dataset.dispatch_status,
                dispatch_dataset.fullname,
                REPLACE(REGEXP_REPLACE(location_sector.code, '[0-9]', ''), '_', '') as 'Area'
            FROM location_sector
            JOIN (
                SELECT
                    dispatch_dispatch.requested_date as 'requested_date',
                    dispatch_schedule.bunny_color as 'bunny_color',
                    dispatch_dispatch.dispatch_status,
                    user_profile_rider.fullname,
                    auth_user.uuid as 'uuid',
                    CAST(JSON_EXTRACT(dispatch_dispatch.sector_list, '$[0]') AS UNSIGNED) AS 'sector_id'
                FROM dispatch_dispatch
                JOIN dispatch_schedule
                ON dispatch_dispatch.schedule_id = dispatch_schedule.id
                JOIN auth_user
                ON dispatch_schedule.rider_id = auth_user.id
                JOIN user_profile_rider
                ON user_profile_rider.user_id = auth_user.id
                WHERE dispatch_dispatch.schedule_id IS NOT NULL
                AND dispatch_dispatch.dispatch_status IN ('SUBMITTED', 'CONFIRMED', 'UNDISPATCHED', 'REFUSED', 'PENDING')
                AND dispatch_dispatch.requested_date = DATE(CONVERT_TZ(UTC_TIMESTAMP(), '+00:00', '+09:00'))
                AND dispatch_schedule.bunny_color NOT IN ('OFFROAD')
            ) dispatch_dataset
            ON location_sector.id = dispatch_dataset.sector_id
            order by 4
        """
        return self.db_handler.fetch_data("daas", query)
