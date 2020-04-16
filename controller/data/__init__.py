from . import view, api, tripitaka

views = [
    tripitaka.TripitakaListHandler, tripitaka.TripitakaViewHandler,
    view.DataListHandler,
]

handlers = [
    api.DataUpsertApi, api.DataUploadApi, api.DataDeleteApi, api.DataGenJsApi,
]
