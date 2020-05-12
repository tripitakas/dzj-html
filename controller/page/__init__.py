from . import view, api, ocr, bak

views = [
    view.PageListHandler, view.PageBrowseHandler, view.PageViewHandler, view.PageInfoHandler,
    view.PageBoxHandler, view.PageOrderHandler, view.PageFindCmpHandler,
    view.PageTaskListHandler, view.PageTaskStatHandler, view.PageTaskResumeHandler,
    view.PageCutTaskHandler, bak.PageTxtTaskHandler, view.PageTxtMatchHandler,
    bak.PageTxtHandler, bak.PageTextHandler,
]

handlers = [
    ocr.FetchTasksApi, ocr.SubmitTasksApi, ocr.ConfirmFetchApi,
    api.PageDeleteApi, api.PageUpsertApi,
    api.PageBoxApi, api.CharBoxApi, api.PageOrderApi, api.PageCmpTxtApi, api.PageCmpTxtNeighborApi,
    api.PageGenCharsApi, api.PageSourceApi,
    api.PageTaskPublishApi, api.PageCutTaskApi, api.PageTxtMatchApi,
    bak.PageTxtDiffApi, bak.PageDetectCharsApi,
]

modules = {'TextArea': bak.TextArea}
