from . import view, api, tripitaka

views = [
    tripitaka.TripitakaListHandler, tripitaka.TripitakaViewHandler,
    view.DataListHandler, view.VariantListHandler,
]

handlers = [
    api.DataUpsertApi, api.DataUploadApi, api.DataDeleteApi, api.DataGenJsApi,
]
