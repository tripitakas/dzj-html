from . import view, api, tripitaka as tri

views = [
    tri.TripitakaListHandler, tri.TripitakaPageHandler, tri.TripitakaDataHandler,
    view.DataListHandler, view.VariantListHandler, view.DataImportImageHandler,
]

handlers = [
    api.DataUpsertApi, api.DataUploadApi, api.DataDeleteApi, api.VariantDeleteApi, api.VariantMergeApi,
    api.VariantSourceApi, api.DataGenJsApi, api.PublishImportImageApi,
]
