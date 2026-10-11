# Hackathon submission — School Air Alert

## Short description

School Air Alert is a mobile-friendly dashboard that helps school staff review
hourly PM2.5 forecasts, see project-policy GREEN/YELLOW/RED labels, and compare
the lowest and highest forecast windows before planning outdoor activities.

## Problem and solution

School staff and families need understandable air-quality information when
planning PE, sports, recess, assemblies, and other outdoor activities. School
Air Alert brings forecast context, a plain-language status, activity-window
decision support, school history, and a printable notice into one interface.
It is informational decision support, not medical advice or a safety
guarantee.

## Target users

Principals, teachers, school administrators, and parents who want an accessible
view of a school's forecast and alert status.

## Features

- Open-Meteo Air Quality API hourly PM2.5 forecast integration through FastAPI.
- Configurable normal and sensitive project-policy classifications.
- School-hour summaries, hourly charts, and best/worst forecast windows.
- Demo mode clearly labelled separately from live provider data.
- English, Hindi, and Marathi interface, history report, and printable poster.
- School and subscription APIs, Telegram webhook/commands, and scheduled alert
  processing implemented locally; real external delivery is not verified.

## Technology

React 18, Vite, JavaScript, responsive CSS, FastAPI, Python 3.12, Open-Meteo,
and an AWS SAM deployment definition for API Gateway, Lambda, DynamoDB,
EventBridge Scheduler, and SNS. Optional Bedrock message generation is
configured server-side.

## Demo and setup

See [`demo-script.md`](demo-script.md) for a short walkthrough and the
[README](../README.md) for prerequisites, local setup, tests, and demo/live
mode instructions. Demo mode requires no AWS account. Live forecasts need the
backend and internet access to Open-Meteo. Telegram delivery needs server-side
credentials and a configured webhook.

## Impact and limitations

The intended impact is to make forecast information easier for schools to
review and communicate. No measured health outcome or user-study impact is
claimed. The configured PM2.5 bands are project placeholders, not official
CPCB AQI categories. F19 forecast-accuracy scoring and F20 NASA FIRMS smoke
hints are pending approved data sources and methods. AWS deployment and
production delivery are not verified.

## Verified links

- Source repository: <https://github.com/rd-111/school-air-alert>
- Public bot link supplied for the project: <https://t.me/schoolalert11_bot>
- Deployed frontend: **not verified / not available**
- Deployed backend API: **not verified / not available**

The source repository and bot URL are provided project links; their live
availability was not verified from this environment.
