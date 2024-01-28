import asyncio
import csv

import aiohttp

from cards import reminder_card
from utils import preferences as p

# Define the path to your file
file_path = "./CSV/20240209-Fuse.csv"

fuse_date = "1/1/2024"
max_retries = 3
retry_delay = 5  # Delay between retries in seconds

post_msg_url = "https://webexapis.com/v1/messages/"

headers = {
    "Authorization": p.test_webex_bearer,
    "Content-Type": "application/json",
}


"""def send_message(email, payload, message_type):
    for i in range(max_retries):
        try:
            response = request("POST", post_msg_url, json=payload, headers=headers)
            response.raise_for_status()
        except exceptions.HTTPError as http_err:
            if response.status_code == 429:
                print("Too many requests, retrying in 5 seconds...")
                sleep(5)  # Adjust this delay if necessary
                continue
            elif i < max_retries - 1:  # i is zero indexed
                print(
                    f"HTTP error occurred: {http_err}. Retrying in {retry_delay} seconds..."
                )
                sleep(retry_delay)
                continue
            else:
                print(
                    f"Failed to send {message_type} message to {email} after {max_retries} attempts due to {http_err}."
                )
                break
        except Exception as err:
            print(f"An error occurred: {err}")
            break
        else:
            print(f"Sent {message_type} message to {email}")
            break"""


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

accept = set()
decline = set()
tentative = set()
no_response = set()

for attendee in attendees:
    if attendee[1] == "Accepted":
        accept.add(attendee[2])
    elif attendee[1] == "Declined":
        decline.add(attendee[2])
    elif attendee[1] == "Tentative":
        tentative.add(attendee[2])
    else:
        no_response.add(attendee[2])

print("Attendees:")
print(f" Accepted: {len(accept)}")
print(f" Declined: {len(decline)}")
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
            "accepted": {"$each": [x for x in accept]},
            "declined": {"$each": [x for x in decline]},
            "tentative": {"$each": [x for x in tentative]},
            "no_response": {"$each": [x for x in no_response]},
        },
    },
)

# Define the sets
message_sets = {
    "accepted": accept,
    "tentative": tentative,
    "no_response": no_response,
}

# Initialize message counter
message_counter = {
    "accepted": 0,
    "tentative": 0,
    "no_response": 0,
}

"""# Iterate over the message types and their respective sets
for message_type, message_set in message_sets.items():
    # Check if the set is not empty
    if message_set:
        # Create the attachment
        attachment = reminder_card.reminder_card(fuse_date, message_type)

        # Iterate over each person in the message_set
        for person in message_set:
            email = f"{person}@cisco.com"

            payload = {
                "toPersonEmail": "aarodavi@cisco.com",  # email,
                "markdown": "Adaptive card response. Open the message on a supported client to respond.",
                "attachments": attachment,
            }
            send_message(email, payload, message_type)"""


async def send_message(session, email, payload, message_type):
    max_retries = 3
    too_many_requests_counter = 0
    too_many_requests_limit = 1
    for i in range(max_retries):
        try:
            async with session.post(
                post_msg_url, json=payload, headers=headers
            ) as response:
                if response.status == 429:
                    # Use the Retry-After header to determine how long to wait
                    retry_after = int(
                        response.headers.get("Retry-After", 5)
                    )  # Default to 5 seconds if Retry-After header is not provided
                    if too_many_requests_counter < too_many_requests_limit:
                        print(
                            f"Too many requests, retrying in {retry_after} seconds..."
                        )
                        too_many_requests_counter += 1
                    await asyncio.sleep(
                        retry_after
                    )  # Pause execution for 'retry_after' seconds
                    continue
                response.raise_for_status()
        except Exception as e:
            print(f"Failed to send {message_type} message to {email} due to {str(e)}")
        else:
            print(f" Sent {message_type} message to {email}")
            # Increment the counter for the message type
            message_counter[message_type] += 1
            break


async def main():
    async with aiohttp.ClientSession() as session:
        tasks = []
        for message_type, message_set in message_sets.items():
            if message_set:
                # Create the attachment inside the loop
                attachment = reminder_card.reminder_card(fuse_date, message_type)
                for person in message_set:
                    email = f"{person}@cisco.com"
                    payload = {
                        "toPersonEmail": p.test_email,  # email,
                        "markdown": "Adaptive card response. Open the message on a supported client to respond.",
                        "attachments": attachment,
                    }
                    tasks.append(send_message(session, email, payload, message_type))

        await asyncio.gather(*tasks)

        # Print the message counter at the end
        print("Sent message count by type:", message_counter)
        print("Total messages sent:", sum(message_counter.values()))


# Run the main function
asyncio.run(main())
