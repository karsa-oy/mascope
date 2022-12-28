from backend.server import sio


@sio.event(namespace='/')
async def instrument_acquisition_finished(sid, acquisition_data):
    await sio.emit(
        'instrument_acquisition_finished',
        acquisition_data,
        room=acquisition_data['instrument'],
        namespace='/'
    )

@sio.event(namespace='/')
async def instrument_acquisition_progress(sid, acquisition_data):
    await sio.emit(
        'instrument_acquisition_progress',
        acquisition_data,
        room=acquisition_data['instrument'],
        namespace='/'
    )

@sio.event(namespace='/')
async def instrument_acquisition_started(sid, acquisition_data):
    await sio.emit(
        'instrument_acquisition_started',
        acquisition_data,
        room=acquisition_data['instrument'],
        namespace='/'
    )