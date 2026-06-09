# API shape references

이 프로젝트는 실제 외부 API를 호출하지 않습니다. 다만 AI가 보는 MCP tool의 이름, 인자, 반환 모양이 너무 장난감처럼 보이지 않도록 아래 공개 API 문서를 참고했습니다.

## Microsoft Graph mail

- `POST /me/sendMail`, `POST /users/{id | userPrincipalName}/sendMail`
- JSON body에 `message`와 선택적 `saveToSentItems`가 들어갑니다.
- 예시 body는 `message.subject`, `message.body.contentType`, `message.body.content`, `toRecipients[].emailAddress.address` 형태입니다.

Project mapping:

```python
graph_me_sendMail(message: dict, saveToSentItems: bool = True)
```

## Gmail messages

- Gmail API `users.messages.list`: `userId`, `q`, `maxResults`, `pageToken` 같은 parameter를 사용합니다.
- Gmail API `users.messages.get`: `userId`, `id`, `format`을 사용합니다.
- Gmail API `users.messages.send`: RFC 2822 email message를 base64url로 인코딩한 `raw` field를 받습니다.

Project mapping:

```python
gmail_users_messages_list(userId="me", q="", maxResults=10, pageToken=None)
gmail_users_messages_get(userId, id, format="full")
gmail_users_messages_send(userId="me", raw="", message=None)
```

## Google Calendar

- Calendar API `events.list`: `calendarId`, `timeMin`, `timeMax`, `q`, `maxResults` 같은 parameter를 사용합니다.
- Calendar API `events.insert`: `calendarId` path parameter와 event resource body를 사용합니다.

Project mapping:

```python
calendar_events_list(calendarId="primary", timeMin=None, timeMax=None, q="", maxResults=10)
calendar_events_insert(calendarId="primary", body=None, sendUpdates="none")
```

## Google Drive

- Drive API `files.list`: `q`, `pageSize`, `pageToken`, `fields` 같은 query parameter를 사용합니다.
- Drive API `files.get/export/create/delete`의 `fileId`, `mimeType`, metadata body 형태를 참고했습니다.

Project mapping:

```python
drive_files_list(q="", pageSize=10, fields="files(id,name,mimeType,modifiedTime)")
drive_files_get(fileId, fields="*")
drive_files_export(fileId, mimeType="text/plain")
drive_files_create(body, media_body="", fields="id,name")
drive_files_delete(fileId)
```

## Slack

- Slack Web API `chat.postMessage`는 channel에 message를 게시하고, 주요 argument로 `channel`, `text`, `blocks`, `thread_ts`를 사용합니다.
- `conversations.history`는 channel의 최근 message를 읽는 API입니다.

Project mapping:

```python
slack_chat_postMessage(channel, text, blocks=None, thread_ts=None)
slack_conversations_history(channel, limit=100, cursor=None)
```

## Plaid

- Plaid `transactions/get`은 `access_token`, `start_date`, `end_date`, 선택적 `options`를 사용합니다.
- `options.count`, `options.offset`, `options.account_ids` 형태를 참고했습니다.

Project mapping:

```python
plaid_transactions_get(access_token, start_date, end_date, options=None)
plaid_accounts_get(access_token="sandbox-user")
plaid_transfer_create(access_token, account_id, amount, ach_class="ppd", description="", idempotency_key=None)
```

## Amadeus / travel-like search

- Amadeus Flight Offers Search는 `originLocationCode`, `destinationLocationCode`, `departureDate`, `adults`, `max` 같은 parameter 형태를 참고했습니다.
- Hotel search는 `cityCode`, `checkInDate`, `checkOutDate`, `adults` 같은 travel API parameter 형태를 참고했습니다.

Project mapping:

```python
amadeus_flight_offers_search(originLocationCode, destinationLocationCode, departureDate, adults=1, max=10)
amadeus_hotel_offers_search(cityCode=None, city=None, checkInDate=None, checkOutDate=None, adults=1, radius=5, ratings=None, max=10)
```

## Not exact clones

MCP tool name은 Python 함수명 제약과 ChatGPT 도구 표시 가독성 때문에 `/`, `.`, `$` 문자를 그대로 쓰지 않고 snake/camel 혼합형으로 바꿨습니다. 예를 들어 실제 HTTP path `/me/sendMail`은 `graph_me_sendMail`로, Slack `chat.postMessage`는 `slack_chat_postMessage`로 노출합니다.
