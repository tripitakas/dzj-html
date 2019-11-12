from . import api, view

views = [
    view.TaskLobbyHandler, view.MyTaskHandler, view.TaskAdminHandler, view.TaskPageInfoHandler,
    view.TaskInfoHandler,
]

handlers = [
    api.GetReadyTasksApi, api.PublishTasksApi, api.AssignTasksApi, api.DeleteTasksApi,
    api.RepublishTaskApi, api.PickTaskApi, api.ReturnTaskApi, api.FinishTaskApi,
    api.LockTaskDataApi, api.UnlockTaskDataApi,  api.InitTasksForTestApi,
]
