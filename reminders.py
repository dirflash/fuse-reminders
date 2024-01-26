import csv

from utils import preferences as p

# Define the path to your file
file_path = "./CSV/20240209-Fuse.csv"

fuse_date = "1/1/2024"

try:
    with open(file_path, "r") as file:
        # Use csv.reader to handle CSV files
        csv_reader = csv.reader(file)

        # Skip the header
        next(csv_reader)

        attendees = []
        for row in csv_reader:
            # Remove the second column and the newline character
            row.pop(1)
            row[-1] = row[-1].strip()

            # Split and strip the required fields
            split_name = row[0].split("(")
            row.append(split_name[1])
            row[0] = split_name[0].rstrip(")").strip()
            row[2] = row[2].rstrip(")")

            attendees.append(row)

except FileNotFoundError:
    print("File not found")
    exit(1)

accepted = set()
declined = set()
tentative = set()
no_response = set()

for attendee in attendees:
    if attendee[1] == "Accepted":
        accepted.add(attendee[2])
    elif attendee[1] == "Declined":
        declined.add(attendee[2])
    elif attendee[1] == "Tentative":
        tentative.add(attendee[2])
    else:
        no_response.add(attendee[2])

print("Attendees:")
print(f" Accepted: {len(accepted)}")
print(f" Declined: {len(declined)}")
print(f" Tentative: {len(tentative)}")
print(f" No response: {len(no_response)}")

# Does cwa_attendees record exist for this date?
if p.cwa_attendees.find_one({"date": fuse_date}):
    print(f"Record for {fuse_date} exists.")
else:
    # Create the record
    p.cwa_attendees.insert_one({"date": fuse_date})
    print(f"Record for {fuse_date} created.")

# Add responses to the database
print("Adding SE responses to the database")
p.cwa_attendees.update_one(
    {"date": fuse_date},
    {
        "$push": {
            "accepted": {"$each": [x for x in accepted]},
            "declined": {"$each": [x for x in declined]},
            "tentative": {"$each": [x for x in tentative]},
            "no_response": {"$each": [x for x in no_response]},
        },
    },
)

print("")
