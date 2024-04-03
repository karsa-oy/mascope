from .. import sio


@sio.event(namespace="/")
async def instrument_acquisition_finished(sid, acquisition_data):
    await sio.emit(
        "instrument_acquisition_finished",
        acquisition_data,
        room=acquisition_data["instrument"],
        namespace="/",
    )


@sio.event(namespace="/")
async def instrument_acquisition_progress(sid, acquisition_data):
    await sio.emit(
        "instrument_acquisition_progress",
        acquisition_data,
        room=acquisition_data["instrument"],
        namespace="/",
    )


@sio.event(namespace="/")
async def instrument_acquisition_started(sid, acquisition_data):
    await sio.emit(
        "instrument_acquisition_started",
        acquisition_data,
        room=acquisition_data["instrument"],
        namespace="/",
    )


@sio.event(namespace="/")
async def instrument_conversion_finished(sid, conversion_data):
    await sio.emit(
        "instrument_conversion_finished",
        conversion_data,
        room=conversion_data["instrument"],
        namespace="/",
    )


@sio.event(namespace="/")
async def instrument_conversion_progress(sid, conversion_data):
    await sio.emit(
        "instrument_conversion_progress",
        conversion_data,
        room=conversion_data["instrument"],
        namespace="/",
    )


@sio.event(namespace="/")
async def instrument_conversion_started(sid, conversion_data):
    await sio.emit(
        "instrument_conversion_started",
        conversion_data,
        room=conversion_data["instrument"],
        namespace="/",
    )
