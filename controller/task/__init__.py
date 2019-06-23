from . import api_common, api_admin, api_text, api_cut, view_admin, view_do, view_lobby, view_my, view_text

views = [
    view_lobby.TaskLobbyHandler, view_my.MyTaskHandler,
    view_admin.TaskCutStatusHandler, view_admin.TaskTextStatusHandler, view_admin.TaskAdminHandler,
    view_do.CutProofDetailHandler, view_do.CutReviewDetailHandler, view_do.CharOrderProofHandler,
    view_text.TextProofHandler, view_text.TextReviewHandler,

]
handlers = [
    api_common.GetPageApi, api_common.PickTaskApi, api_common.ReturnTaskApi, api_common.UnlockDataApi,
    api_cut.SaveCutProofApi, api_cut.SaveCutReviewApi,
    api_text.SaveTextProofApi, api_text.SaveTextReviewApi,
    api_admin.PublishTasksPageNamesApi, api_admin.PublishTasksFileApi, api_admin.WithDrawTasksApi,
    api_admin.GetReadyPagesApi,
]
modules = {'TextArea': view_text.TextArea}
