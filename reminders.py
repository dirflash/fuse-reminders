import asyncio
import csv
import json
import sys
from time import perf_counter, sleep

import aiohttp
from pymongo import UpdateOne
from pymongo.errors import BulkWriteError, ConnectionFailure

from cards import reminder_card as rc
from utils import preferences as p

# Define the path to your file
file_path = "./CSV/20240308-Fuse.csv"

fuse_date = "3/8/2024"
retry_delay = 5  # Delay between retries in seconds

post_msg_url = "https://webexapis.com/v1/messages/"

headers = {
    "Authorization": p.fusebot_help_bearer,
    "Content-Type": "application/json",
}

start_timer = perf_counter()


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
                            f" Too many requests, retrying in {retry_after} seconds..."
                        )
                        too_many_requests_counter += 1
                    await asyncio.sleep(
                        retry_after
                    )  # Pause execution for 'retry_after' seconds
                    continue
                if response.status == 200:
                    print(
                        f" Sent {message_type} message to {email} ({response.status})"
                    )
                    response_text = await response.text()
                    message_id = json.loads(response_text)["id"]
                    # Increment the counter for the message type
                    message_counter[message_type] += 1
                    return [message_id, email, 200]
                print(f" Unexpected status ({response.status}) sending to {email}")
                return None
        except Exception as e:
            print(f" Failed to send {message_type} message to {email} due to {str(e)}")


async def main():
    async with aiohttp.ClientSession() as session:
        tasks = []
        markdown_msg = (
            "Adaptive card response. Open the message on a supported client to respond."
        )
        for message_type, message_set in message_sets.items():
            if message_set:
                # Create the attachment inside the loop
                attachment = rc.reminder_card(fuse_date, message_type)
                for person in message_set:
                    email = (
                        f"{person}@cisco.com"  # < --- change to p.test_email for test
                    )
                    payload = {
                        "toPersonEmail": email,
                        "markdown": markdown_msg,
                        "attachments": attachment,
                    }
                    tasks.append(send_message(session, email, payload, message_type))

        results = await asyncio.gather(*tasks)

        # Update the reminders database with the message status and message id
        if results is not None:
            operations = []
            for i, result in enumerate(results):
                try:
                    message_id, email, status = result  # Attempt to unpack the tuple
                    print(f"Adding {email} message status to reminders database")
                    alias = email.replace("@cisco.com", "")
                    operations.append(
                        UpdateOne(
                            {"date": fuse_date},
                            {"$set": {alias: [message_id, email, status]}},
                            upsert=True,
                        )
                    )
                except TypeError as te:
                    print(f"TypeError for record {result}: {te} - skipping record")
                    continue  # Skip this record and continue with the next

            # Only perform the bulk write if there are operations to execute
            if operations:
                for attempt in range(5):
                    try:
                        reminder_updates = p.cwa_reminders.bulk_write(operations)
                        if reminder_updates.upserted_ids:
                            print(
                                f"MongoDB upserted {len(reminder_updates.upserted_ids)} records."
                            )
                        break  # Exit the retry loop if successful
                    except BulkWriteError as bwe:
                        print("Bulk Write Error: ", bwe.details)
                        sleep_duration = pow(2, attempt)
                        print(
                            f"*** Sleeping for {sleep_duration} seconds and trying again ***"
                        )
                        sleep(sleep_duration)  # Exponential backoff
                    except Exception as e:
                        print("An unexpected error occurred: ", e)
                        break  # Exit the retry loop if an unexpected exception occurs

        # Print the message counter at the end
        print("Sent message count by type:", message_counter)
        print("Total messages sent:", sum(message_counter.values()))


try:
    with open(file_path, "r", encoding="utf-8") as file:
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
    sys.exit(1)

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
for _ in range(5):
    try:
        if p.cwa_attendees.find_one({"date": fuse_date}):
            print(f" Record for {fuse_date} exists.")
        else:
            # Create the record
            p.cwa_attendees.insert_one({"date": fuse_date})
            print(f" Record for {fuse_date} created.")
        break
    except ConnectionFailure as cf:
        print(" Connection Failure looking up attendees record: ", cf)
        print("  *** Sleeping for {pow(2, _)} seconds and trying again ***")
        sleep(pow(2, _))

# Add responses to the database
print("Adding SE responses to attendees database")
for _ in range(5):
    try:
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
        break
    except ConnectionFailure as cf:
        print(" Connection Failure adding responses to attendees database: ", cf)
        print("  *** Sleeping for {pow(2, _)} seconds and trying again ***")
        sleep(pow(2, _))

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

# Run the main function
asyncio.run(main())

stop_timer = perf_counter()
print(f"Time: {stop_timer - start_timer:.2f} seconds")
