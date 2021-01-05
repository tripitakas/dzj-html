from . import view, api, tripitaka

views = [
    tripitaka.TripitakaListHandler, tripitaka.TripitakaViewHandler, tripitaka.TptkViewHandler,
    view.DataListHandler, view.VariantListHandler, tripitaka.TptkMetaHandler,
    view.DataImportImageHandler,
]

handlers = [
    api.DataUpsertApi, api.DataUploadApi, api.DataDeleteApi, api.VariantDeleteApi, api.VariantMergeApi,
    api.VariantSourceApi, api.DataGenJsApi, api.PublishImportImageApi, api.PageExportApi,
]
