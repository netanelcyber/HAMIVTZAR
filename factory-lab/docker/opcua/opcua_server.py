#!/usr/bin/env python3
"""OPC-UA Server for factory simulation."""

import asyncio
import logging
from datetime import datetime
from asyncua import ua, Server
from asyncua.common import callback

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OPCUAServer:
    def __init__(self):
        self.server = None
        self.root = None
        self.objects = None

    async def init(self):
        """Initialize OPC-UA server."""
        self.server = Server()
        await self.server.init()

        self.server.set_endpoint("opc.tcp://0.0.0.0:4840/factory/server")

        # Set server info
        info = ua.ServerInfo()
        info.ProductName = "Factory SCADA Server"
        info.ManufacturerName = "Factory Lab"
        info.SoftwareVersion = "1.0.0"
        self.server.set_server_info(info)

        # Get root
        self.root = self.server.get_root_node()
        self.objects = self.server.get_objects_node()

        # Setup namespace
        uri = "http://factory.local/opcua"
        idx = await self.server.register_namespace(uri)

        # Create folders
        factory_folder = await self.objects.add_folder(idx, "Factory")
        production_folder = await factory_folder.add_folder(idx, "Production")
        equipment_folder = await factory_folder.add_folder(idx, "Equipment")
        alarms_folder = await factory_folder.add_folder(idx, "Alarms")

        # Create production line variables
        for line_num in range(1, 6):
            line_folder = await production_folder.add_folder(idx, f"Line_{line_num}")

            # Production line variables
            await line_folder.add_variable(
                idx, "Status",
                ua.Variant(True if line_num < 5 else False, ua.VariantType.Boolean)
            )
            await line_folder.add_variable(
                idx, "Speed",
                ua.Variant(85.0 + (line_num * 2), ua.VariantType.Float)
            )
            await line_folder.add_variable(
                idx, "Temperature",
                ua.Variant(70.0 + (line_num * 0.5), ua.VariantType.Float)
            )
            await line_folder.add_variable(
                idx, "Pressure",
                ua.Variant(29.0 + (line_num * 0.4), ua.VariantType.Float)
            )
            await line_folder.add_variable(
                idx, "ProductionRate",
                ua.Variant(line_num * 150, ua.VariantType.Int32)
            )
            await line_folder.add_variable(
                idx, "DefectRate",
                ua.Variant(0.5 + (line_num * 0.1), ua.VariantType.Float)
            )

        # Equipment health
        for equip_num in range(1, 8):
            equip_folder = await equipment_folder.add_folder(idx, f"Equipment_{equip_num}")

            status = "Operational" if equip_num != 4 else "Maintenance"
            await equip_folder.add_variable(
                idx, "Status",
                ua.Variant(status, ua.VariantType.String)
            )
            await equip_folder.add_variable(
                idx, "OperatingHours",
                ua.Variant(equip_num * 1000, ua.VariantType.Int32)
            )
            await equip_folder.add_variable(
                idx, "MaintenanceIntervalDays",
                ua.Variant(30, ua.VariantType.Int32)
            )
            await equip_folder.add_variable(
                idx, "LastMaintenanceDate",
                ua.Variant(datetime.now().isoformat(), ua.VariantType.String)
            )

        # Alarms
        await alarms_folder.add_variable(
            idx, "ActiveAlarms",
            ua.Variant(2, ua.VariantType.Int32)
        )
        await alarms_folder.add_variable(
            idx, "LastAlarmTime",
            ua.Variant(datetime.now().isoformat(), ua.VariantType.String)
        )

        logger.info("OPC-UA server initialized")

    async def start(self):
        """Start OPC-UA server."""
        async with self.server:
            logger.info("OPC-UA server started on opc.tcp://0.0.0.0:4840")
            while True:
                await asyncio.sleep(1)

async def main():
    """Main entry point."""
    server = OPCUAServer()
    await server.init()
    await server.start()

if __name__ == "__main__":
    asyncio.run(main())
