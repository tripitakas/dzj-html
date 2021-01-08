from . import view, api, api_task as at, view_task as vt, api_ocr as ao

views = [
    view.PageListHandler, view.PageStatisticHandler, view.PageBrowseHandler, view.PageViewHandler,
    view.PageInfoHandler, view.PageBoxHandler, view.PageTxtHandler,
    view.PageTxtMatchHandler, view.PageFindCmpHandler,
    vt.PageTaskCutHandler, vt.PageTaskTextHandler, vt.PageTaskDashBoardHandler,
    vt.PageTaskListHandler, vt.PageTaskStatisticHandler, vt.PageTaskResumeHandler,
    view.PageBlockHandler,
]

handlers = [
    api.PageDeleteApi, api.PageUpsertApi, api.PageUploadApi, api.PageSourceApi,
    api.PageCmpTxtApi, api.PageFindCmpTxtApi, api.PageCmpTxtNeighborApi,
    api.PageBoxApi, api.PageCharBoxApi, api.PageCharTxtApi,
    api.PageTxtDiffApi, api.PageTxtMatchApi, api.PageTxtMatchDiffApi,
    api.PageStartGenCharsApi, api.PageStartCheckMatchApi,
    at.PageTaskListApi, at.PageTaskPublishApi, at.PageTaskCutApi, at.PageTaskTextApi,
    ao.FetchTasksApi, ao.SubmitTasksApi, ao.ConfirmFetchApi,
    api.PageBlocksApi,
]
