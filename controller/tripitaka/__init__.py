from . import view, api

views = [
    view.RsTripitakaHandler, view.TripitakaListHandler, view.TripitakaHandler,
]

handlers = [
    api.TripitakaUploadApi
]
