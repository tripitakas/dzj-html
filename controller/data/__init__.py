from . import view, tripitaka, volume, sutra, reel

views = [
    view.DataTripitakaHandler, view.DataVolumeHandler, view.DataSutraHandler, view.DataReelHandler,
    view.TripitakaListHandler, view.TripitakaHandler,
    view.DataPageHandler,
]

handlers = [
    tripitaka.TripitakaAddOrUpdateApi, tripitaka.TripitakaUploadApi, tripitaka.TripitakaDeleteApi,
    volume.VolumeAddOrUpdateApi, volume.VolumeUploadApi, volume.VolumeDeleteApi,
    sutra.SutraAddOrUpdateApi, sutra.SutraUploadApi, sutra.SutraDeleteApi,
    reel.ReelAddOrUpdateApi, reel.ReelUploadApi, reel.ReelDeleteApi,
]
