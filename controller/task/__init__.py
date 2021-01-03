from . import api, view

views = [
    view.PageTaskLobbyHandler, view.CharTaskLobbyHandler, view.MyPageTaskHandler,
    view.MyCharTaskHandler, view.TaskInfoHandler, view.TaskSampleHandler,
]

handlers = [
    api.PickTaskApi, api.ReturnTaskApi, api.UpdateTaskApi, api.RepublishTaskApi,
    api.DeleteTasksApi, api.AssignTasksApi, api.FinishTaskApi,
    api.UpdateTaskMyRemarkApi, api.InitTasksForOPTestApi,
]
