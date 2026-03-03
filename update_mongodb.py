# import pandas as pd
# from pymongo import MongoClient
# import re
# import ftfy

# # connect to mongo
# MONGO_URI = "mongodb+srv://jchan51_db_user:Aliciarivera2%40@cluster0.hxeytkt.mongodb.net/"
# client = MongoClient(MONGO_URI)
# db = client["pls"]
# users_collection = db["users"]

# # load updated CSV
# user_df = pd.read_csv("final_user_batches.csv", encoding="latin1")

# ALL_TYPES = {
#     "static_1", "static_2",
#     "interactive_3", "interactive_4",
#     "finetuned_5", "finetuned_6",
# }

# def clean_text(x):
#     if pd.isna(x):
#         return ""
#     return re.sub(r"\s+", " ", ftfy.fix_text(str(x))).strip()

# def allowed_types_from_checkpoint(last_full_type):
#     """
#     Checkpoint logic:
#     - last_full_type == "static_1": update static_2 + interactives + finetuned
#     - last_full_type == "static_2": update interactives + finetuned
#     - last_full_type starts with interactive_/finetuned_: update interactives + finetuned
#     - missing/empty: update everything (static_1 included)
#     """
#     if not last_full_type or str(last_full_type).strip() == "":
#         return ALL_TYPES  # new user

#     last_full_type = str(last_full_type).strip()

#     if last_full_type == "static_1":
#         return ALL_TYPES - {"static_1"}
#     if last_full_type == "static_2":
#         return {"interactive_3", "interactive_4", "finetuned_5", "finetuned_6"}
#     if last_full_type.startswith("interactive_") or last_full_type.startswith("finetuned_"):
#         return {"interactive_3", "interactive_4", "finetuned_5", "finetuned_6"}

#     # fallback: conservative (don't touch static_1)
#     return ALL_TYPES - {"static_1"}

# updated_ops = 0
# skipped_ops = 0
# skipped_no_rows = 0

# for user in users_collection.find({}, {"prolific_id": 1, "last_full_type": 1}):
#     prolific_id = user.get("prolific_id")
#     if not prolific_id:
#         continue

#     allowed_types = allowed_types_from_checkpoint(user.get("last_full_type"))

#     user_rows = user_df[user_df["user_id"] == prolific_id]
#     if user_rows.empty:
#         skipped_no_rows += 1
#         continue

#     for _, row in user_rows.iterrows():
#         full_type = row["type"]
#         if full_type not in allowed_types:
#             skipped_ops += 1
#             continue

#         phase_type, batch_id = full_type.split("_")
#         abstract_key = str(row["abstract_id"])

#         update_fields = {
#             f"phases.{phase_type}.batches.{batch_id}.abstracts.{abstract_key}.abstract_title":
#                 clean_text(row.get("abstract_title", "")),

#             f"phases.{phase_type}.batches.{batch_id}.abstracts.{abstract_key}.abstract":
#                 clean_text(row.get("abstract", "")),

#             f"phases.{phase_type}.batches.{batch_id}.abstracts.{abstract_key}.human_written_pls":
#                 clean_text(row.get("human_written", "")),

#             # Questions (1–5)
#             f"phases.{phase_type}.batches.{batch_id}.abstracts.{abstract_key}.question_1":
#                 row.get("question_1", ""),
#             f"phases.{phase_type}.batches.{batch_id}.abstracts.{abstract_key}.question_2":
#                 row.get("question_2", ""),
#             f"phases.{phase_type}.batches.{batch_id}.abstracts.{abstract_key}.question_3":
#                 row.get("question_3", ""),
#             f"phases.{phase_type}.batches.{batch_id}.abstracts.{abstract_key}.question_4":
#                 row.get("question_4", ""),
#             f"phases.{phase_type}.batches.{batch_id}.abstracts.{abstract_key}.question_5":
#                 row.get("question_5", ""),

#             # Answer choices + correct answers (1–5)
#             f"phases.{phase_type}.batches.{batch_id}.abstracts.{abstract_key}.question_1_answers_choices":
#                 row.get("question_1_answers_choices", ""),
#             f"phases.{phase_type}.batches.{batch_id}.abstracts.{abstract_key}.question_1_correct_answers":
#                 row.get("question_1_correct_answers", ""),

#             f"phases.{phase_type}.batches.{batch_id}.abstracts.{abstract_key}.question_2_answers_choices":
#                 row.get("question_2_answers_choices", ""),
#             f"phases.{phase_type}.batches.{batch_id}.abstracts.{abstract_key}.question_2_correct_answers":
#                 row.get("question_2_correct_answers", ""),

#             f"phases.{phase_type}.batches.{batch_id}.abstracts.{abstract_key}.question_3_answers_choices":
#                 row.get("question_3_answers_choices", ""),
#             f"phases.{phase_type}.batches.{batch_id}.abstracts.{abstract_key}.question_3_correct_answers":
#                 row.get("question_3_correct_answers", ""),

#             f"phases.{phase_type}.batches.{batch_id}.abstracts.{abstract_key}.question_4_answers_choices":
#                 row.get("question_4_answers_choices", ""),
#             f"phases.{phase_type}.batches.{batch_id}.abstracts.{abstract_key}.question_4_correct_answers":
#                 row.get("question_4_correct_answers", ""),

#             f"phases.{phase_type}.batches.{batch_id}.abstracts.{abstract_key}.question_5_answers_choices":
#                 row.get("question_5_answers_choices", ""),
#             f"phases.{phase_type}.batches.{batch_id}.abstracts.{abstract_key}.question_5_correct_answers":
#                 row.get("question_5_correct_answers", ""),
#         }

#         users_collection.update_one(
#             {"prolific_id": prolific_id},
#             {"$set": update_fields}
#         )
#         updated_ops += 1

# print("Migration complete.")
# print("Updated ops:", updated_ops)
# print("Skipped ops (checkpoint-protected):", skipped_ops)
# print("Users missing in CSV:", skipped_no_rows)

import pandas as pd
from pymongo import MongoClient

# -------- CONFIG --------
MONGO_URI = "mongodb+srv://jchan51_db_user:Aliciarivera2%40@cluster0.hxeytkt.mongodb.net/"
CSV_PATH = "final_user_batches.csv"          # your "final_df" source
DRY_RUN = False                             # set False to actually delete
BATCH_ORDER = ["static_1","static_2","interactive_3","interactive_4","finetuned_5","finetuned_6"]
# ------------------------

client = MongoClient(MONGO_URI)
db = client["pls"]
users_collection = db["users"]

df = pd.read_csv(CSV_PATH, encoding="latin1")

# Build: allowed[(prolific_id, full_type)] = set(abstract_id strings)
allowed = {}
for _, row in df.iterrows():
    pid = str(row["user_id"]).strip()
    full_type = str(row["type"]).strip()          # e.g., "static_2"
    abs_id = str(row["abstract_id"]).strip()      # store as string because Mongo keys are strings
    allowed.setdefault((pid, full_type), set()).add(abs_id)

total_users_scanned = 0
total_unsets = 0
total_removed_keys = 0

for user in users_collection.find({}, {"prolific_id": 1, "phases": 1}):
    pid = str(user.get("prolific_id", "")).strip()
    phases = user.get("phases", {})
    if not pid:
        continue

    total_users_scanned += 1

    unset_ops = {}
    removed_here = 0

    for full_type in BATCH_ORDER:
        phase_type, batch_id = full_type.split("_")   # phase_type: static/interactive/finetuned, batch_id: "1","2","3"...
        mongo_batch = (
            phases.get(phase_type, {})
                  .get("batches", {})
                  .get(batch_id, {})
        )

        if not mongo_batch:
            continue

        mongo_abstracts = mongo_batch.get("abstracts", {})
        if not isinstance(mongo_abstracts, dict) or len(mongo_abstracts) == 0:
            continue

        allowed_ids = allowed.get((pid, full_type), set())

        # Any keys present in Mongo but not in CSV assignment → remove
        extra_ids = [abs_id for abs_id in mongo_abstracts.keys() if abs_id not in allowed_ids]

        for abs_id in extra_ids:
            unset_path = f"phases.{phase_type}.batches.{batch_id}.abstracts.{abs_id}"
            unset_ops[unset_path] = ""   # $unset value can be anything
            removed_here += 1

    if unset_ops:
        total_unsets += 1
        total_removed_keys += removed_here

        print(f"\n[PRUNE] prolific_id={pid} removing {removed_here} extra abstract(s)")
        # show what will be removed (optional)
        for k in list(unset_ops.keys())[:25]:
            print("  -", k)
        if len(unset_ops) > 25:
            print(f"  ... +{len(unset_ops)-25} more")

        if not DRY_RUN:
            users_collection.update_one({"prolific_id": pid}, {"$unset": unset_ops})

print("\nDONE")
print("Users scanned:", total_users_scanned)
print("Users with removals:", total_unsets)
print("Total abstracts removed:", total_removed_keys)
print("DRY_RUN:", DRY_RUN)