from . import view, api, tripitaka

views = [
    tripitaka.TripitakaListHandler, tripitaka.TripitakaViewHandler, tripitaka.TptkViewHandler,
    view.DataListHandler, view.VariantListHandler,
]

handlers = [
    api.DataUpsertApi, api.DataUploadApi, api.DataDeleteApi, api.VariantDeleteApi,
    api.DataGenJsApi,
]
