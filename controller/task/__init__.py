import controller.task.api_base
from . import api_base, api_publish, api_text, api_cut, view_admin, view_cut, view_lobby, view_my, view_text

views = [
    view_lobby.TaskLobbyHandler, view_my.MyTaskHandler,
    view_admin.TaskCutStatusHandler, view_admin.TaskTextStatusHandler, view_admin.TaskAdminHandler,
    view_cut.CutProofHandler, view_cut.CutReviewHandler,
    view_cut.CharOrderProofHandler, view_cut.CharOrderReviewHandler,
    view_text.TextFindCmpHandler, view_text.TextProofHandler, view_text.TextReviewHandler, view_text.TextHardHandler,
]
handlers = [
    api_base.PickTaskApi, api_base.ReturnTaskApi, api_base.UnlockTaskDataApi, api_base.WithDrawTasksApi,
    api_cut.SaveCutApi, api_text.SaveTextProofApi, api_text.SaveTextReviewApi, api_text.SaveTextHardApi,
    api_base.GetPageApi, api_text.GetCmpTextApi, api_text.GetCmpNeighborApi, api_text.SaveCmpTextApi,
    api_publish.GetReadyPagesApi, api_publish.PublishTasksPageNamesApi, api_publish.PublishTasksPagePrefixApi,

]
modules = {'TextArea': view_text.TextArea}
