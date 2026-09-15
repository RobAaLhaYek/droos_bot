import logging
from pathlib import Path
from typing import Any

from gspread_pandas import Client, Spread, conf
from pandas import DataFrame
from pyarabic.trans import convert as transliterate

logger = logging.getLogger(__name__)


class Spreadsheet:
    def __init__(
        self,
        service_account: str,
        sheet_id: str,
        sheet_name: str,
        data_columns: dict[str, str],
        lecture_components: dict[str, str],
    ) -> None:
        self._client: Client = Client(
            config=conf.get_config(
                conf_dir=str(Path(service_account).parent),
                file_name=service_account,
            )
        )

        self.data_columns = data_columns
        self.lecture_components = lecture_components

        self.worksheet: Spread = Spread(
            sheet_id,
            sheet=sheet_name,
            client=self._client,
        )

        self.df: DataFrame = self.worksheet.sheet_to_df(index=0)



        # Create slug columns for every hierarchy column
        for column_id in data_columns:
            self.df[f"{column_id}_slug"] = self.df[column_id].apply(
                lambda x: "_".join(
                    transliterate(
                        str(x),
                        "arabic",
                        "tim",
                    )
                    .lower()
                    .replace("\\", "")
                    .split(" ")
                )
            )

        # Create a unique ID for every lecture
        self.df["id"] = self.df.apply(
            lambda row: "_".join(
                [
                    row[f"{column_id}_slug"]
                    for column_id in data_columns
                    if str(row.get(column_id, "")).strip()
                ]
                + [str(row.get("lecture", ""))]
            ),
            axis=1,
        )

        self.hierarchy = self.create_hierarchy(
            data_columns,
            lecture_components,
        )

    def refresh(self) -> None:
        self.df = self.worksheet.sheet_to_df(index=0)

        for column_id in self.data_columns:
            self.df[f"{column_id}_slug"] = self.df[column_id].apply(
                lambda x: "_".join(
                    transliterate(str(x), "arabic", "tim")
                    .lower()
                    .replace("\\", "")
                    .split(" ")
                )
            )

        self.df["id"] = self.df.apply(
            lambda row: "_".join(
                [
                    row[f"{column_id}_slug"]
                    for column_id in self.data_columns
                    if str(row.get(column_id, "")).strip()
                ]
                + [str(row.get("lecture", ""))]
            ),
            axis=1,
        )

        self.hierarchy = self.create_hierarchy(
            self.data_columns,
            self.lecture_components,
        )

    def create_hierarchy(
        self,
        data_columns: dict[str, str],
        lecture_components: dict[str, str],
    ) -> dict[str, Any]:
        hierarchy: dict[str, Any] = {}

        for _, row in self.df.iterrows():
            current_level = hierarchy

            # Build hierarchy according to data_columns order
            for column_id in data_columns:
                value = str(row.get(column_id, "")).strip()

                if not value or value.lower() == "nan":
                    continue

                if value not in current_level:
                    current_level[value] = {}

                current_level = current_level[value]

            lecture_name = str(row.get("lecture", "")).strip()

            if not lecture_name or lecture_name.lower() == "nan":
                continue

            current_level[lecture_name] = {
                component: row.get(component)
                for component in lecture_components
            } | {
                "__data": True,
                "id": row.get("id"),
            }

        return hierarchy

    def navigate_hierarchy(self, path: list[str]) -> dict | None:
        current_level = self.hierarchy

        for item in path:
            if item in current_level:
                current_level = current_level[item]
            else:
                return None

        return current_level