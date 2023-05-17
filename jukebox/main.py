#  Copyright (c) 2023 JukeBox Developers - All Rights Reserved
#  This file is part of the JukeBox Music App and is released under the "MIT License Agreement"
#  Please see the LICENSE file that should have been included as part of this package

from fastapi import FastAPI
from jukebox import globals
from jukebox.database.core import init_db, close_db

app = FastAPI(
    title="JukeBox Music App",
    version=globals.version,
    docs_url='/docs',
    redoc_url=None,  # disable
)


@app.on_event('startup')
async def startup():
    await init_db()


@app.on_event('shutdown')
async def shutdown():
    await close_db()
