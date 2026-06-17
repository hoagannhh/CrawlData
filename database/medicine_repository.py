from datetime import datetime
from database.db_connect import get_connection
from utils.helpers import make_id
from utils.logger import get_logger

logger = get_logger("medicine_repository")


class MedicineRepository:

    def insert(self, record: dict) -> bool:
        """Chèn 1 record, bỏ qua nếu URL đã tồn tại."""
        sql = """
            INSERT OR IGNORE INTO medicines
                (id, source, url, name, active_ingredient, drug_class,
                 indication, dosage, adverse_effect, contraindication, description, scraped_at)
            VALUES
                (:id, :source, :url, :name, :active_ingredient, :drug_class,
                 :indication, :dosage, :adverse_effect, :contraindication, :description, :scraped_at)
        """
        record = {**record, "id": make_id(record.get("url", "")), "scraped_at": datetime.now()}
        try:
            with get_connection() as conn:
                cur = conn.execute(sql, record)
                return cur.rowcount > 0
        except Exception as e:
            logger.error(f"Insert lỗi: {e} | url={record.get('url')}")
            return False

    def insert_many(self, records: list[dict]) -> int:
        """Chèn nhiều records, trả về số lượng đã chèn thành công."""
        inserted = sum(1 for r in records if self.insert(r))
        logger.info(f"Đã chèn {inserted}/{len(records)} records vào DB")
        return inserted

    def url_exists(self, url: str) -> bool:
        with get_connection() as conn:
            row = conn.execute("SELECT 1 FROM medicines WHERE url = ?", (url,)).fetchone()
            return row is not None

    def count_by_source(self) -> dict:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT source, COUNT(*) as cnt FROM medicines GROUP BY source"
            ).fetchall()
            return {r["source"]: r["cnt"] for r in rows}

    def get_all(self, source: str = None) -> list[dict]:
        with get_connection() as conn:
            if source:
                rows = conn.execute(
                    "SELECT * FROM medicines WHERE source = ? ORDER BY scraped_at", (source,)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM medicines ORDER BY source, scraped_at"
                ).fetchall()
            return [dict(r) for r in rows]

    def get_non_empty_fields(self) -> dict:
        """Thống kê số record có nội dung cho từng field — hữu ích khi kiểm tra chất lượng."""
        fields = ["active_ingredient", "drug_class", "indication",
                  "dosage", "adverse_effect", "contraindication", "description"]
        stats = {}
        with get_connection() as conn:
            for f in fields:
                row = conn.execute(
                    f"SELECT COUNT(*) as cnt FROM medicines WHERE {f} != '' AND {f} IS NOT NULL"
                ).fetchone()
                stats[f] = row["cnt"]
        return stats