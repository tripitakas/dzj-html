from . import view, api, tripitaka as tri

views = [
    tri.TripitakaListHandler, tri.TripitakaViewHandler, tri.TptkViewHandler, tri.TptkMetaHandler,
    view.DataListHandler, view.VariantListHandler, view.DataImportImageHandler,
]

handlers = [
    api.DataUpsertApi, api.DataUploadApi, api.DataDeleteApi, api.VariantDeleteApi,
    api.VariantMergeApi, api.DataGenJsApi, api.PublishImportImageApi,
]
