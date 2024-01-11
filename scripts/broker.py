import asyncio
import json
from contextlib import asynccontextmanager
from aio_pika.abc import (
    AbstractChannel, AbstractExchange, AbstractQueue, AbstractRobustConnection)
from aio_pika import connect_robust
from typing import AsyncGenerator
from enum import Enum
from pydantic import BaseModel, ConfigDict
from datetime import datetime


class Plant(str, Enum):
    '''Внутреннее название завода.
    '''
    RZ = 'rz'
    NZ = 'nz'


class PlantLine(str, Enum):
    '''Внутреннее название линии.
    '''
    LINE_1 = 'line_1'
    LINE_2 = 'line_2'
    LINE_3 = 'line_3'
    LINE_4 = 'line_4'


class Item(BaseModel):
    '''Изделие, которое было произведено на линии.
    '''
    barcode: str
    product: str
    production_thickness: float
    max_length: float
    max_width: float


class DBEntry(BaseModel):
    '''Запись в базе данных.

    Содержит информацию о том, что было произведено на линии.
    Items может содержать несколько изделий.
    '''
    location_name: str
    pal_no: int
    timestamp: datetime
    items: list[Item]


class ObserverMessage(BaseModel):
    '''Сообщение, отправляемое/получаемое из очереди.

    Содержит информацию о заводе, линии и новой записи в базе данных.
    '''
    model_config = ConfigDict(arbitrary_types_allowed=True)

    plant: Plant
    line: PlantLine
    entry: DBEntry


class MessageQueue:
    '''Класс для взаимодействия с брокером сообщений.

    Основная задача - создать подключение к брокеру.

    Пример использования:
    ---------------------

    mq = MessageQueue('vhost', 'user', 'password', 'server', 5672)
    async with mq.connect() as connection:
        ...
    '''

    def __init__(
            self, v_host: str, username: str, password: str, server: str,
            port: int) -> None:

        v_host = v_host
        user = username
        pwd = password
        host = server
        port = port

        self.c_str = f'amqp://{user}:{pwd}@{host}:{port}/{v_host}'

    @asynccontextmanager
    async def connect(self) -> AsyncGenerator[AbstractRobustConnection, None]:
        self.connection = await connect_robust(self.c_str)
        yield self.connection
        await self.connection.close()

    def get_connection(self) -> AbstractRobustConnection:
        return self.connection

    async def __aenter__(self):
        self.connection = await connect_robust(self.c_str)
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self.connection:
            await self.connection.close()


class Broker:
    '''Класс определяющий очереди (queues), обменники (exchanges) и 
    привязки (bindings).

    В данном случае используется только один обменник типа topic.

    Пример использования:
        # создание подключения к брокеру
        mq = MessageQueue('vhost', 'user', 'password', 'server', 5672)

        async with mq.connect() as connection:
            # создание канала

            async with connection.channel() as channel:
                # создание брокера
                async with Broker(channel) as broker:
                    ...
    '''

    def __init__(self, channel: AbstractChannel):
        self.channel = channel

    async def __aenter__(self):
        channel = self.channel

        # exchanges
        self.exchange_topic = await channel.declare_exchange(
            'topic', type='topic', durable=True)

        # queues
        ...

        # bindings
        ...

        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass

    def get_exchange(self, exchange_key: str) -> AbstractExchange:
        key = f'exchange_{exchange_key}'
        if not hasattr(self, key):
            raise AttributeError(f'Exchange {exchange_key} does not exist.')
        attr = getattr(self, key)
        if not isinstance(attr, AbstractExchange):
            raise AttributeError(f'Exchange {exchange_key} is not an exchange.')
        return getattr(self, key)

    async def create_topic_queue(
            self, queue_name: str, routing_key: str) -> AbstractQueue:
        queue = await self.channel.declare_queue(queue_name, durable=False)
        await queue.bind(self.exchange_topic, routing_key=routing_key)
        return queue


class DBObserverRepository:
    '''Класс для взаимодействия с очередью.

    Основная задача - создать очередь, которая будет получать сообщения из
    обменника типа topic.

    Атрибуты:
        broker: Брокер, который будет использоваться для очереди.

    Пример использования:
        repo = DBObserverRepository(broker)

        async for entry in repo.get_db_entry_feed():
            # entry - новая запись в БД
            ...
    '''

    def __init__(self, broker: Broker) -> None:
        self.broker = broker
        self.queues: dict[str, AbstractQueue] = {}
        self.queue_count: int = 0

    async def get_db_entry_feed(self) -> AsyncGenerator[ObserverMessage, None]:
        '''Создает новую очередь, которая будет получать сообщения из
        обменника типа topic.

        '''
        topic = f'db-location-events'
        self.queue_count += 1
        count = self.queue_count
        key = f'{topic}-{count}'
        queue = await self.broker.create_topic_queue(key, topic)
        self.queues[key] = queue
        async with queue.iterator() as iter:
            async for message in iter:
                async with message.process():
                    print(message.body.decode())
                    if message.content_type == 'application/json':
                        entry = ObserverMessage.model_validate_json(
                            message.body.decode())
                        yield entry
#         test_json = {"plant":"rz","line":"line_1",
# "entry":{"location_name":"TP 1","pal_no":5,"timestamp":"2024-01-11T13:36:00.150000Z",
# 	"items":[{"barcode":"122000136301","product":"1_3НСНг-289.299.41-3-8_21.04.2023 16.04.31.uni","production_thickness":410.0,"max_length":2985.0,"max_width":2885.0},
# 		{"barcode":"122000132807","product":"2_3НСг-217.299.29-1-4_07.12.2023 15.27.24.uni","production_thickness":285.0,"max_length":2985.0,"max_width":2165.0}]}}
                        
#         json_object = json.dumps(test_json)
#         entry = ObserverMessage.model_validate_json(
#             json_object)
#         await asyncio.sleep(1)
#         yield entry
        