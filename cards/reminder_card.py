from utils import preferences as p


def accepted_body(s_date):
    body_1 = (
        f"Hello SE! We noticed you are confirmed for the next Fuse session on {s_date}. "
        f"Your confirmation helps us to plan the pairings."
    )
    return body_1


def tentative_body(s_date):
    body_1 = (
        f"Hello SE! We noticed you are tentative for the next Fuse session on {s_date}. "
        f"Your confirmation helps us to plan the pairings."
    )
    return body_1


def no_response_body(s_date):
    body_1 = (
        f"Hello SE! We noticed you have not confirmed your availability for the next Fuse session on {s_date}. "
        f"Your confirmation helps us to plan the pairings."
    )
    return body_1


def reminder_card(s_date, card_type):
    if card_type == "accepted":
        body_1 = accepted_body(s_date)
    elif card_type == "tentative":
        body_1 = tentative_body(s_date)
    elif card_type == "no_response":
        body_1 = no_response_body(s_date)

    body_2 = (
        "We are looking forward to hearing about the new SE connection you make. "
        "Thanks again, and we will see you in a couple of days!"
    )

    send_card = {
        "contentType": "application/vnd.microsoft.card.adaptive",
        "content": {
            "type": "AdaptiveCard",
            "body": [
                {
                    "type": "ImageSet",
                    "images": [
                        {
                            "type": "Image",
                            "size": "Medium",
                            "url": p.logo_url,
                            "height": "100px",
                            "width": "400px",
                        }
                    ],
                },
                {
                    "type": "Container",
                    "items": [
                        {
                            "type": "TextBlock",
                            "text": "Fuse Session RSVP Confirmation",
                            "wrap": True,
                            "horizontalAlignment": "Center",
                            "fontType": "Monospace",
                            "size": "Large",
                            "weight": "Bolder",
                        },
                        {
                            "type": "TextBlock",
                            "text": body_1,
                            "wrap": True,
                            "fontType": "Monospace",
                            "size": "Default",
                            "weight": "Bolder",
                        },
                        {
                            "type": "TextBlock",
                            "wrap": True,
                            "text": body_2,
                            "fontType": "Monospace",
                            "weight": "Bolder",
                            "size": "Default",
                        },
                    ],
                },
            ],
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "version": "1.2",
        },
    }
    return send_card
