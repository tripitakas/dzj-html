from . import api, view

views = [
    view.TaskLobbyHandler, view.MyTaskHandler, view.PageTaskAdminHandler, view.TaskAdminImageHandler,
    view.PageTaskResumeHandler, view.PageTaskStatisticHandler,
    view.TaskDetailHandler,
]

handlers = [
    api.PublishManyPageTasksApi, api.PublishImportImageTasksApi, api.RepublishTaskApi,
    api.GetReadyTasksApi, api.AssignTasksApi, api.DeleteTasksApi, api.TaskUpdateApi,
    api.PickTaskApi, api.ReturnTaskApi, api.FinishTaskApi, api.LockTaskDataApi,
    api.UnlockTaskDataApi, api.InitTasksForTestApi,
]
