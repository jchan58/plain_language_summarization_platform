import pandas as pd
from pymongo import MongoClient
import re
import ftfy

# connect to mongo
MONGO_URI = "mongodb+srv://jchan51_db_user:Aliciarivera2%40@cluster0.hxeytkt.mongodb.net/"
client = MongoClient(MONGO_URI)
db = client["pls"]
users_collection = db["users"]

# load updated CSV
user_df = pd.read_csv("final_user_batches.csv", encoding="latin1")

# batches to update (skip static_1)
BATCHES_TO_UPDATE = [
    "static_2",
    "interactive_3",
    "interactive_4",
    "finetuned_5",
    "finetuned_6",
]

for user in users_collection.find():
    prolific_id = user["prolific_id"]

    user_rows = user_df[user_df["user_id"] == prolific_id]

    for _, row in user_rows.iterrows():
        full_type = row["type"]

        if full_type not in BATCHES_TO_UPDATE:
            continue  # skip static_1

        phase_type, batch_id = full_type.split("_")
        abstract_key = str(row["abstract_id"])

        update_fields = {
            f"phases.{phase_type}.batches.{batch_id}.abstracts.{abstract_key}.abstract_title":
                row["abstract_title"],

            f"phases.{phase_type}.batches.{batch_id}.abstracts.{abstract_key}.abstract":
                re.sub(r"\s+", " ", ftfy.fix_text(row["abstract"])).strip(),

            f"phases.{phase_type}.batches.{batch_id}.abstracts.{abstract_key}.human_written_pls":
                re.sub(r"\s+", " ", ftfy.fix_text(row["human_written"])).strip(),

            # Questions
            f"phases.{phase_type}.batches.{batch_id}.abstracts.{abstract_key}.question_1":
                row["question_1"],
            f"phases.{phase_type}.batches.{batch_id}.abstracts.{abstract_key}.question_2":
                row["question_2"],
            f"phases.{phase_type}.batches.{batch_id}.abstracts.{abstract_key}.question_3":
                row["question_3"],
            f"phases.{phase_type}.batches.{batch_id}.abstracts.{abstract_key}.question_4":
                row["question_4"],
            f"phases.{phase_type}.batches.{batch_id}.abstracts.{abstract_key}.question_5":
                row["question_5"],

            # Answer choices + correct answers
            f"phases.{phase_type}.batches.{batch_id}.abstracts.{abstract_key}.question_1_answers_choices":
                row["question_1_answers_choices"],
            f"phases.{phase_type}.batches.{batch_id}.abstracts.{abstract_key}.question_1_correct_answers":
                row["question_1_correct_answers"],

            f"phases.{phase_type}.batches.{batch_id}.abstracts.{abstract_key}.question_2_answers_choices":
                row["question_2_answers_choices"],
            f"phases.{phase_type}.batches.{batch_id}.abstracts.{abstract_key}.question_2_correct_answers":
                row["question_2_correct_answers"],

            f"phases.{phase_type}.batches.{batch_id}.abstracts.{abstract_key}.question_3_answers_choices":
                row["question_3_answers_choices"],
            f"phases.{phase_type}.batches.{batch_id}.abstracts.{abstract_key}.question_3_correct_answers":
                row["question_3_correct_answers"],

            f"phases.{phase_type}.batches.{batch_id}.abstracts.{abstract_key}.question_4_answers_choices":
                row["question_4_answers_choices"],
            f"phases.{phase_type}.batches.{batch_id}.abstracts.{abstract_key}.question_4_correct_answers":
                row["question_4_correct_answers"],

            f"phases.{phase_type}.batches.{batch_id}.abstracts.{abstract_key}.question_5_answers_choices":
                row["question_5_answers_choices"],
            f"phases.{phase_type}.batches.{batch_id}.abstracts.{abstract_key}.question_5_correct_answers":
                row["question_5_correct_answers"],
        }

        users_collection.update_one(
            {"prolific_id": prolific_id},
            {"$set": update_fields}
        )

print("Migration complete.")