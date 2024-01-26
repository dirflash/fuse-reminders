import csv

# Define the path to your file
file_path = "./CSV/20240209-Fuse.csv"

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

print(f"Accepted ({len(accepted)})")
print(f"Declined ({len(declined)})")
print(f"Tentative ({len(tentative)})")
print(f"No response ({len(no_response)})")
