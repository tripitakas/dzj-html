from . import view, api, tripitaka

views = [
    view.RsTripitakaHandler, view.TripitakaListHandler, view.TripitakaHandler,
]

handlers = [
    tripitaka.TripitakaAddOrUpdateApi, tripitaka.TripitakaUploadApi, tripitaka.TripitakaDeleteApi
]
