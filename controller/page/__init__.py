from . import api, view, ocr, data

views = [
    data.PageAdminHandler, data.PageViewHandler, data.PageInfoHandler,
    view.PageTaskCutHandler, view.PageCutEditHandler,
    view.PageTaskTextProofHandler, view.PageTaskTextReviewHandler, view.PageTextEditHandler,
]

handlers = [
    data.PageUpdateSourceApi, data.PageExportCharApi, data.PageUploadApi,
    api.PageTaskCutApi, api.PageCutEditApi,
    api.PageTaskTextSelectApi, api.PageTaskTextProofApi, api.PageTaskTextReviewApi, api.PageTaskTextHardApi,
    api.PageTextEditApi, api.PageNeighborTextApi, api.PageDiffTextsApi, api.PageDetectWideCharsApi,
    ocr.FetchOcrTasksApi, ocr.SubmitOcrTasksApi, ocr.ConfirmFetchOcrTasksApi,
]

modules = {'TextArea': view.TextArea}
