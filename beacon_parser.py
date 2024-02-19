#!/usr/bin/env python3

import binascii
import datetime
import argparse
from pprint import pformat
from typing import List, Optional
from rich import print
from struct import unpack, unpack_from

import datacache as datacache


class enum_UHF_Beacon:
    UHF_BEACON_TYPE_0 = 0x80
    UHF_BEACON_TYPE_1 = 0x81
    UHF_BEACON_TYPE_2 = 0x82
    UHF_BEACON_TYPE_3 = 0x83
    OBC_BEACON = 0x33


class enum_Byte_Stuffing:
    FRAME_ESC = 0x20
    FRAME_BEGIN = 0x21
    FRAME_END = 0x22


class data_deserializer:
    def __init__(self) -> None:
        self.partial_message = False
        self.temp_beacontype = 0
        self.dcp = datacache.dc_parser()
        self.str_from_parsed_dict = ""

    def deserialize(self, bcn_type, data):
        (deser_data, bytes_cnt) = self.dcp.parse_by_id(bcn_type, data)
        return (deser_data, bytes_cnt)

    def parse_object(self, deser_obj: dict, ident=8):
        str_space_val = "  ".ljust(ident)

        try:
            for key, value in deser_obj.items():
                if (type(value) is list and "libs.mac" in str(value)) or (
                    type(value) is list and "libs.fidl" in str(value)
                ):
                    for item in value:
                        attribute_dict = vars(item)
                        self.parse_object(attribute_dict, ident + 1)
                else:
                    self.str_from_parsed_dict += "{}{:<22}:           {}\n".format(
                        str_space_val, key, value
                    )
        except Exception as e:
            print(f"Cannot recursively deserialize data > {e}")


class parser_utils:
    """various functions and factors when parsing data"""

    def __init__(self) -> None:
        self.units = {
            "seconds": "{sec}",
            "miliV": "{mV}",
            "volt": "{V}",
            "amp": "{A}",
            "miliamp": "{mA}",
            "centigrade": "{°C}",
            "ohm": "{Ω}",
        }

    def volt(self, data, flag: str):
        if flag == "battery":
            return data * 0.0023394775
        elif flag == "bcr":
            return data * 0.0024414063
        elif flag == "panel":
            return data * 0.0024414063
        else:
            raise Exception("invalid voltage flag for parsing..")

    def current(self, data, flag: str):
        if flag == "battery":
            return data * 3.0517578
        elif flag == "bcr":
            return data * 1.5258789
        elif flag == "panel":
            return data * 0.6103516
        elif flag == "bus":
            return data * 2.0345052
        else:
            raise Exception("invalid current flag for parsing..")

    def resistance(self, data):
        return data * 1.4972656

    def temp(self, data, flag: str):
        if flag == "mcu":
            return ((data * 0.0006103516) - 0.986) / 0.00355
        elif flag == "2s_complement":
            if data < 32768:
                formatted_data = data * 0.00390625
            else:
                formatted_data = (((data >> 4) - 1) ^ 0xFFF) * (-0.0625)
            return formatted_data

    def format_temp(self, temp_val):
        if temp_val < 32768:
            formatted_temp_val = temp_val * 0.00390625
        else:
            formatted_temp_val = (((temp_val >> 4) - 1) ^ 0xFFF) * (-0.0625)
        return formatted_temp_val


class UHF_payload_parser:
    def __init__(self) -> None:
        self.packet_info = None
        self.beacon_data = None
        self.bcn_hdr: Optional[frame_hdr] = None
        self.unpacked_data = None
        self.parse_flag: bool = True
        self.subsystem_beacon = None
        self.util = parser_utils()
        self.obc_parser = None

    def reset_data(self):
        self.beacon_data = None

    def parse_data(self):
        # [case] UHF Beacon Type [0]
        if self.bcn_hdr.bcn_msg_id == enum_UHF_Beacon.UHF_BEACON_TYPE_0:
            self.subsystem_beacon = "UHF"

            parsed_data = (bytes(self.beacon_data)).decode("ascii")

            self.display_beacon(parsed_data)

        # [case] UHF Beacon Type [1]
        elif self.bcn_hdr.bcn_msg_id == enum_UHF_Beacon.UHF_BEACON_TYPE_1:
            self.subsystem_beacon = "UHF"

            fmt = "<%dH" % (len(self.beacon_data) // 2)  # data is all uint16
            self.unpacked_data = list(unpack(fmt, bytes(self.beacon_data)))

            scw = self.unpacked_data[0]
            v_batt = self.unpacked_data[1]
            i_batt = self.unpacked_data[2]
            v_bcr = self.unpacked_data[3]
            i_bcr = self.unpacked_data[4]
            v_x = self.unpacked_data[5]
            i_xm = self.unpacked_data[6]
            i_xp = self.unpacked_data[7]
            v_y = self.unpacked_data[8]
            i_ym = self.unpacked_data[9]
            i_yp = self.unpacked_data[10]
            v_z = self.unpacked_data[11]
            i_zm = self.unpacked_data[12]
            i_zp = self.unpacked_data[13]
            i_3V3 = self.unpacked_data[14]
            i_5V = self.unpacked_data[15]
            t_mcu = self.unpacked_data[16]
            t_batt1 = self.unpacked_data[17]
            t_batt2 = self.unpacked_data[18]
            t_batt3 = self.unpacked_data[19]
            t_batt4 = self.unpacked_data[20]
            cnd_input = self.unpacked_data[21]
            cnd_output1 = self.unpacked_data[22]
            cnd_output2 = self.unpacked_data[23]
            por_cycles = self.unpacked_data[24]
            v_under = self.unpacked_data[25]
            v_short = self.unpacked_data[26]
            v_overtemp = self.unpacked_data[27]
            t_max1 = self.unpacked_data[28]
            t_min1 = self.unpacked_data[29]
            def1 = self.unpacked_data[30]
            def2 = self.unpacked_data[31]
            r_batt = self.unpacked_data[32]
            v_ideal_batt = self.unpacked_data[33]

            beacon_struct = {
                "UHF Status Control Word         :   ": [hex(scw)],
                "EPS I Battery Voltage           :   ": [
                    float(self.util.volt(v_batt, "battery")),
                    self.util.units["volt"],
                ],
                "EPS I Battery Current           :   ": [
                    float(self.util.current(i_batt, "battery")),
                    self.util.units["miliamp"],
                ],
                "BCR Voltage                     :   ": [
                    float(self.util.volt(v_bcr, "bcr")),
                    self.util.units["volt"],
                ],
                "BCR Current                     :   ": [
                    float(self.util.current(i_bcr, "bcr")),
                    self.util.units["miliamp"],
                ],
                "SOL PAN X V                     :   ": [
                    float(self.util.volt(v_x, "panel")),
                    self.util.units["volt"],
                ],
                "SOL PAN X- Current              :   ": [
                    float(self.util.current(i_xm, "panel")),
                    self.util.units["miliamp"],
                ],
                "SOL PAN X+ Current              :   ": [
                    float(self.util.current(i_xp, "panel")),
                    self.util.units["miliamp"],
                ],
                "SOL PAN Y V                     :   ": [
                    float(self.util.volt(v_y, "panel")),
                    self.util.units["volt"],
                ],
                "SOL PAN Y- Current              :   ": [
                    float(self.util.current(i_ym, "panel")),
                    self.util.units["miliamp"],
                ],
                "SOL PAN Y+ Current              :   ": [
                    float(self.util.current(i_yp, "panel")),
                    self.util.units["miliamp"],
                ],
                "SOL PAN Z V                     :   ": [
                    float(self.util.volt(v_z, "panel")),
                    self.util.units["volt"],
                ],
                "SOL PAN Z- Current              :   ": [
                    float(self.util.current(i_zm, "panel")),
                    self.util.units["miliamp"],
                ],
                "SOL PAN Z+ Current              :   ": [
                    float(self.util.current(i_zp, "panel")),
                    self.util.units["miliamp"],
                ],
                "3.3V Bus Current                :   ": [
                    float(self.util.current(i_3V3, "bus")),
                    self.util.units["miliamp"],
                ],
                "5V   Bus Current                :   ": [
                    float(self.util.current(i_5V, "bus")),
                    self.util.units["miliamp"],
                ],
                "MCU Temperature                 :   ": [
                    float(self.util.temp(t_mcu, "mcu")),
                    self.util.units["centigrade"],
                ],
                "Battery Cell 1 Temp             :   ": [
                    float(self.util.temp(t_batt1, "2s_complement")),
                    self.util.units["centigrade"],
                ],
                "Battery Cell 2 Temp             :   ": [
                    float(self.util.temp(t_batt2, "2s_complement")),
                    self.util.units["centigrade"],
                ],
                "Battery Cell 3 Temp             :   ": [
                    float(self.util.temp(t_batt3, "2s_complement")),
                    self.util.units["centigrade"],
                ],
                "Battery Cell 4 Temp             :   ": [
                    float(self.util.temp(t_batt4, "2s_complement")),
                    self.util.units["centigrade"],
                ],
                "Input Condition                 :   ": [hex(cnd_input)],
                "Output Conditions 1             :   ": [hex(cnd_output1)],
                "Output Conditions 2             :   ": [hex(cnd_output2)],
                "Power ON Cycle Counter          :   ": [por_cycles],
                "Under Voltage Cond Counter      :   ": [hex(v_under)],
                "Short Circuit Cond Counter      :   ": [hex(v_short)],
                "Over Temp Cond Counter          :   ": [hex(v_overtemp)],
                "Battpack1 temp sensor 1 max temp:   ": [
                    float(self.util.temp(t_max1, "2s_complement")),
                    self.util.units["centigrade"],
                ],
                "Battpack1 temp sensor 1 min temp:   ": [
                    float(self.util.temp(t_min1, "2s_complement")),
                    self.util.units["centigrade"],
                ],
                "Default Vals LUPs & fastcharge  :   ": [hex(def1)],
                "Default Vals OUTs 1:6           :   ": [hex(def2)],
                "Battery Internal Resistance     :   ": [
                    float(self.util.resistance(r_batt)),
                    self.util.units["ohm"],
                ],
                "Battery Ideal Voltage           :   ": [
                    float(self.util.volt(v_ideal_batt, "battery")),
                    self.util.units["volt"],
                ],
            }

            # display beacon
            self.display_beacon(beacon_struct)

        # [case] UHF Beacon Type [2]
        elif self.bcn_hdr.bcn_msg_id == enum_UHF_Beacon.UHF_BEACON_TYPE_2:
            self.subsystem_beacon = "UHF"

            uint8_t_fmt = "<B"
            uint16_t_fmt = "<H"
            int16_t_fmt = "<h"
            uint32_t_fmt = "<I"

            scw = unpack(uint16_t_fmt, bytes(self.beacon_data[:2]))
            uptime = unpack(uint32_t_fmt, bytes(self.beacon_data[2:6]))
            mcu_temp = unpack(int16_t_fmt, bytes(self.beacon_data[6:8]))
            rssi_pend = unpack(uint8_t_fmt, bytes(self.beacon_data[8:9]))
            rssi_stat = unpack(uint8_t_fmt, bytes(self.beacon_data[9:10]))
            rssi_curr = unpack(uint8_t_fmt, bytes(self.beacon_data[10:11]))
            rssi_latc = unpack(uint8_t_fmt, bytes(self.beacon_data[11:12]))
            rssi_ant1 = unpack(uint8_t_fmt, bytes(self.beacon_data[12:13]))
            rssi_ant2 = unpack(uint8_t_fmt, bytes(self.beacon_data[13:14]))
            afc_f_off = unpack(uint16_t_fmt, bytes(self.beacon_data[14:16]))
            tx_packet = unpack(uint32_t_fmt, bytes(self.beacon_data[16:20]))
            rx_packet = unpack(uint32_t_fmt, bytes(self.beacon_data[20:24]))
            rxpkt_crc = unpack(uint32_t_fmt, bytes(self.beacon_data[24:28]))
            lst_phnxm = unpack(uint32_t_fmt, bytes(self.beacon_data[28:32]))
            lst_nrmm = unpack(uint32_t_fmt, bytes(self.beacon_data[32:36]))

            beacon_struct = {
                "UHF Status Control Word         :   ": [hex(scw[0])],
                "UHF Uptime (hex, dec)           :   ": [
                    hex(uptime[0]),
                    uptime[0],
                    self.util.units["seconds"],
                ],
                "MCU Temperature                 :   ": [
                    float(mcu_temp[0] / 10),
                    self.util.units["centigrade"],
                ],
                "RSSI Modem Pending              :   ": [hex(rssi_pend[0])],
                "RSSI Modem Status               :   ": [hex(rssi_stat[0])],
                "RSSI Current                    :   ": [hex(rssi_curr[0])],
                "RSSI Latch                      :   ": [hex(rssi_latc[0])],
                "RSSI Antenna 1                  :   ": [hex(rssi_ant1[0])],
                "RSSI Antenna 2                  :   ": [hex(rssi_ant2[0])],
                "AFC Frequency Offset            :   ": [hex(afc_f_off[0])],
                "Transmitted Packets             :   ": [hex(tx_packet[0])],
                "Received Packets                :   ": [hex(rx_packet[0])],
                "Received Packets with CRC Error :   ": [hex(rxpkt_crc[0])],
                "Last Phoenix Mode Time          :   ": [hex(lst_phnxm[0])],
                "Last Normal Mode Time           :   ": [hex(lst_nrmm[0])],
            }

            self.display_beacon(beacon_struct)

        # [case] UHF Beacon Type [3]
        elif self.bcn_hdr.bcn_msg_id == enum_UHF_Beacon.UHF_BEACON_TYPE_3:
            self.subsystem_beacon = "UHF"

            uint16_t_fmt = "<H"
            uint32_t_fmt = "<I"

            scw = unpack(uint16_t_fmt, bytes(self.beacon_data[:2]))
            conops_m = unpack(uint16_t_fmt, bytes(self.beacon_data[2:4]))
            por_cycles = unpack(uint32_t_fmt, bytes(self.beacon_data[4:8]))
            mac_collis = unpack(uint32_t_fmt, bytes(self.beacon_data[8:12]))
            mac_failur = unpack(uint32_t_fmt, bytes(self.beacon_data[12:16]))
            gs_handshk = unpack(uint32_t_fmt, bytes(self.beacon_data[16:20]))
            nvm_writef = unpack(uint32_t_fmt, bytes(self.beacon_data[20:24]))
            nvm_readf = unpack(uint32_t_fmt, bytes(self.beacon_data[24:28]))
            nvmdef_en = unpack(uint32_t_fmt, bytes(self.beacon_data[28:32]))
            fram_intc = unpack(uint32_t_fmt, bytes(self.beacon_data[32:36]))
            fram_extc = unpack(uint32_t_fmt, bytes(self.beacon_data[36:40]))
            fram_extg = unpack(uint32_t_fmt, bytes(self.beacon_data[40:44]))

            beacon_struct = {
                "UHF Status Control Word         :   ": [hex(scw[0])],
                "ConOps Mode                     :   ": [hex(conops_m[0])],
                "Power On Cycle Counter          :   ": [hex(por_cycles[0])],
                "MAC Collision Counter           :   ": [hex(mac_collis[0])],
                "MAC Network Fail Counter        :   ": [hex(mac_failur[0])],
                "GS Handshake Counter            :   ": [hex(gs_handshk[0])],
                "NVM Write Fail Counter          :   ": [hex(nvm_writef[0])],
                "NVM Read Fail Counter           :   ": [hex(nvm_readf[0])],
                "NVM Default Entry Counter       :   ": [hex(nvmdef_en[0])],
                "Internal FRAM Corruption Counter:   ": [hex(fram_intc[0])],
                "External FRAM Corruption Counter:   ": [hex(fram_extc[0])],
                "External FRAM NResponsive (GONE):   ": [hex(fram_extg[0])],
            }

            self.display_beacon(beacon_struct)

        # [case] Other subsystems
        elif self.bcn_hdr.bcn_msg_id == enum_UHF_Beacon.OBC_BEACON:
            self.subsystem_beacon = "OBC"
            self.display_beacon()
        else:
            self.reset_data()
            raise Exception("invalid beacon message id")

    def display_beacon(self, msg_struct=None):
        ts = datetime.datetime.now().strftime("%H:%M:%S.%f")
        ts = datetime.time.fromisoformat(ts)

        if self.subsystem_beacon == "UHF":
            data = binascii.hexlify(bytes(self.beacon_data))

            data_parsed = pformat(msg_struct)

            stamp_hdr = f"\n{ts} [[bold magenta]UHF[/bold magenta]] BeaconFrame> [ bcn_number: {self.bcn_hdr.bcn_seq_num} | subsystem: {self.subsystem_beacon} | parse_flag: {self.parse_flag}]:\n"

            # if self.parse_flag:
            #     print_str = (
            #         stamp_hdr
            #         + f"\t[prs] => BeaconMsg> [ BeaconMsgHdr> bcn_type: {hex(self.bcn_hdr.bcn_msg_id)} | len: {len(self.beacon_data)} ] => \n{data_parsed}"
            #     )

            #     print(print_str)
            # else:
            #     print_str = (
            #         stamp_hdr
            #         + f"\t[raw] => BeaconMsg> [ BeaconMsgHdr> bcn_type: {hex(self.bcn_hdr.bcn_msg_id)} | len: {len(self.beacon_data)} ] => {data}"
            #     )

            # print(print_str)

        elif self.subsystem_beacon == "OBC":
            data = bytes(self.beacon_data)
            ts = datetime.datetime.now().strftime("%H:%M:%S.%f")
            ts = datetime.time.fromisoformat(ts)

            FP_HDR_SIZE = 10
            if len(data) > FP_HDR_SIZE:
                if not self.obc_parser.parse_beacon_frame(ts, data):
                    print(
                        f":exclamation_mark: {ts} empty or invalid frame => [{data}]")


class frame_hdr:
    AX_25_BCN_FRAME_PLD_HDR_SZ = 3

    def __init__(self) -> None:
        self.bcn_seq_num: int = 0
        self.bcn_uhf_id: int = 0
        self.bcn_uhf_op_mode: int = 0
        self.bcn_msg_id: int = 0

    def parse(self, hdr_data: bytes):
        (
            self.bcn_seq_num,
            self.bcn_uhf_id,
            self.bcn_uhf_op_mode,
            self.bcn_msg_id,
        ) = unpack_from("BBBB", bytes(hdr_data))
        return 0


class frame_parser:
    def __init__(self, obc_parser) -> None:
        self.res()
        self.obc_parser = obc_parser
        self.is_bcn_valid: bool = False

    def res(self):
        self.buf = []
        self.in_frame = False
        self.escape_pending = False

    def decode(self, byte: bytes):
        byte = byte & 0xFF

        if byte == enum_Byte_Stuffing.FRAME_BEGIN:
            self.in_frame = True
            self.buf = []
        else:
            if self.in_frame:
                if byte == enum_Byte_Stuffing.FRAME_END:
                    self.parse_frame(self.buf, self.obc_parser)
                    self.res()
                else:
                    if byte == enum_Byte_Stuffing.FRAME_ESC:
                        self.escape_pending = True
                    else:
                        if self.escape_pending:
                            self.buf.append((~byte) & 0xFF)
                            self.escape_pending = False
                        else:
                            self.buf.append(byte)

    def parse_frame(self, buffer: List[bytes], obc_parser) -> bool:
        # Byte sequence looked for in the AX.25 frame
        # 0xE1 -> SSID 22
        # 0x03 -> CONTROL 23
        # 0xF0 -> PID3 24

        HDR_SIZE = 37  # header
        FTR_SIZE = 4  # supposed footer
        CTRL_SEQ = [0xE1, 0x03, 0xF0]  # control sequence (AX.25)

        # frame header
        bcn_hdr = frame_hdr()
        BEACON_CONSEC_NUM_INDEX_OFFSET = 3
        BEACON_MSG_ID_OFFSET = 7

        buff_idx = 0

        while buff_idx < len(buffer):
            if (
                (buffer[buff_idx] == 0xE1)
                and (buffer[buff_idx + 1] == 0x03)
                and (buffer[buff_idx + 2] == 0xF0)
            ):
                self.is_bcn_valid: bool = True

                # parse header
                bcn_hdr.parse(
                    buffer[
                        buff_idx
                        + BEACON_CONSEC_NUM_INDEX_OFFSET: buff_idx
                        + BEACON_MSG_ID_OFFSET
                    ]
                )  # parse bcn hdr

                # get data
                payload_data = buffer[
                    buff_idx + BEACON_MSG_ID_OFFSET: -FTR_SIZE
                ]  # get payload data

                if ((bcn_hdr.bcn_msg_id == 0x80) or (bcn_hdr.bcn_msg_id == 0xFF)) or (
                    (bcn_hdr.bcn_msg_id > 0x80) and (bcn_hdr.bcn_msg_id < 0xFF)
                ):
                    # Beacon source is UHF
                    parser = UHF_payload_parser()
                    parser.beacon_data = payload_data
                    parser.bcn_hdr = bcn_hdr
                    parser.parse_data()
                    parser.reset_data()

                elif ((bcn_hdr.bcn_msg_id == 0x00) or (bcn_hdr.bcn_msg_id == 0x7F)) or (
                    (bcn_hdr.bcn_msg_id > 0x00) and (bcn_hdr.bcn_msg_id < 0x7F)
                ):
                    if bcn_hdr.bcn_msg_id == 0x33:
                        # source is OBC
                        parser = UHF_payload_parser()
                        parser.beacon_data = payload_data
                        parser.bcn_hdr = bcn_hdr
                        parser.obc_parser = obc_parser
                        parser.parse_data()
                        parser.reset_data()
                    else:
                        # source is some other subsys
                        pass

            elif (buffer[30:33] == CTRL_SEQ) and (
                (len(buffer) < (HDR_SIZE + 6))
            ):  # 4 bytes msg hdr + 2 bytes minimum payload
                self.is_bcn_valid: bool = False
                print("frame with invalid beacon size received..")
            else:
                self.is_bcn_valid: bool = False

            buff_idx += 1

        return self.is_bcn_valid


class MessageAssembler:
    def __init__(self, deserializer):
        self.data_piece = b""
        self.data_piece_bcn_type = 0
        self.full_data_len = 0
        self.full_data = b""
        self.deserializer: data_deserializer = deserializer

    def assemble_message(self, full_assembled_data):
        self.full_data = full_assembled_data

    def length(self):
        return len(self.data_piece)

    def reset_buffer(self):
        self.data_piece = b""

    def display_assembled_msg(self):
        (data, bytes_cnt) = self.deserializer.deserialize(
            self.data_piece_bcn_type, self.full_data
        )
        self.deserializer.parse_object(data.__dict__)
        deserialized__d: str = f"\nDeserialized [{bytes_cnt} ->\n[magenta][{self.deserializer.str_from_parsed_dict}][/magenta]"
        self.deserializer.str_from_parsed_dict = ""
        # printout: str = f"\t[[red]c[/red]] => Assembled> [ BeaconMsgHdr> bcn_type: {self.data_piece_bcn_type} | len: {self.full_data_len} | bytes_cnt: {bytes_cnt} ] => {int(self.length())}: [red]{data}[/red]\n"
        # printout += deserialized__d
        # print(printout)


class BeaconMsgHdr:
    HDR_SIZE = 4
    INVALID_BEACON_SLOT_ASSIGNMENT = 0xFFFF

    def __init__(self):
        self.bcn_type = BeaconMsgHdr.INVALID_BEACON_SLOT_ASSIGNMENT
        self.data_status = 0
        self.len = 0

    def parse(self, data: bytes) -> int:
        if len(data) >= BeaconMsgHdr.HDR_SIZE:
            self.bcn_type, self.data_status, self.len = unpack_from(
                "HBB", data)
            return BeaconMsgHdr.HDR_SIZE
        else:
            return 0

    def is_valid(self) -> bool:
        return self.bcn_type != BeaconMsgHdr.INVALID_BEACON_SLOT_ASSIGNMENT

    def __str__(self):
        # return f"BeaconMsgHdr> bcn_type: {self.bcn_type} | status: {self.data_status} | len: {self.len}"
        return ""


class BeaconMessage:
    def __init__(self, parent: "BeaconFrame", deserializer):
        self.hdr = None
        self.data = bytes()
        self.partial_message = False
        self.parent = parent
        self.deserializer: data_deserializer = deserializer

    def parse_message(self, msg_data: bytes) -> int:
        bytes_parsed = 0

        self.hdr = BeaconMsgHdr()
        hdr_bytes = self.hdr.parse(msg_data)

        if self.hdr.is_valid():
            self.data = msg_data[hdr_bytes: hdr_bytes + self.hdr.len]
            self.partial_message = len(self.data) < self.hdr.len
            bytes_parsed = hdr_bytes + len(self.data)

        return bytes_parsed

    def append_data(self, msg: "BeaconMessage") -> tuple:
        if (msg.hdr.bcn_type == self.hdr.bcn_type) and (msg.parent == self.parent):
            self.data += msg.data
            self.partial_message = len(self.data) == self.hdr.len
            return (True, self.partial_message)
        else:
            return (False, self.partial_message)

    def display_beacon_message(self):
        # raw_data_string: str = f"BeaconMsg> [ {self.hdr} ] => {len(self.data)}: {binascii.hexlify(self.data)},"
        raw_data_string: str = ""
        if len(self.data) != self.hdr.len:
            self.deserializer.partial_message = True
            self.deserializer.temp_beacontype = self.hdr.bcn_type
        elif len(self.data) == self.hdr.len:
            if (self.deserializer.temp_beacontype == self.hdr.bcn_type) and (
                self.deserializer.partial_message == True
            ):
                pass
            else:
                self.deserializer.partial_message = False
                self.deserializer.temp_beacontype = 0

                (data, bytes_cnt) = self.deserializer.deserialize(
                    self.hdr.bcn_type, self.data
                )

                # deserialize object and reset string buffer
                self.deserializer.parse_object(data.__dict__)
                raw_data_string: str = (
                    f"Name: {data}"
                )
                deserialized__d: str = f"\n{self.deserializer.str_from_parsed_dict}"
                raw_data_string += deserialized__d
                self.deserializer.str_from_parsed_dict = ""

        return raw_data_string


class BeaconFrameHdr:
    HDR_SIZE = 3
    BEACON_FRAME_FLAG_CONTINUATION = 0x01

    def __init__(self):
        self.bcn_number = 0
        self.op_mode = 0
        self.flags = 0

    def parse(self, data: bytes) -> int:
        if len(data) >= BeaconFrameHdr.HDR_SIZE:
            (self.bcn_number, self.op_mode, self.flags) = unpack_from("BBB", data)

            return BeaconFrameHdr.HDR_SIZE
        else:
            return 0

    def is_split_frame(self) -> bool:
        return self.flags & BeaconFrameHdr.BEACON_FRAME_FLAG_CONTINUATION

    def __str__(self):
        # return f"BeaconFrmHdr> bcn_number: {self.bcn_number} | op_mode: {self.op_mode} | split: {self.is_split_frame()}"
        return ""


class BeaconFrame:
    BCN_FRAME_SIZE = 73

    def __init__(self, deserializer: data_deserializer):
        self.hdr = None
        self.beacon_messages: List[BeaconMessage] = []
        self.is_split_frame = False
        self.timestamp: "datetime.time" = None
        self.deserializer = deserializer

    def parse_beacon_frame(
        self, timestamp: "datetime.time", frame_data: bytes, assembler: MessageAssembler
    ) -> bool:
        self.timestamp = timestamp
        offset = 0
        msg_count_in_frame = 0

        # parse beacon frame header
        self.hdr = BeaconFrameHdr()

        offset += self.hdr.parse(frame_data)

        self.is_split_frame = self.hdr.is_split_frame()

        # parse individual messages in the frame
        while offset < len(frame_data):
            bcn_msg = BeaconMessage(self, self.deserializer)

            bytes_parsed = bcn_msg.parse_message(frame_data[offset:])

            if bytes_parsed > 0:
                msg_count_in_frame += 1

                offset += bytes_parsed

                self.beacon_messages.append(bcn_msg)

                if bcn_msg.hdr.len > len(bcn_msg.data):
                    if assembler.data_piece_bcn_type != bcn_msg.hdr.bcn_type:
                        assembler.full_data_len = bcn_msg.hdr.len
                        assembler.data_piece_bcn_type = bcn_msg.hdr.bcn_type
                    assembler.data_piece += bytearray(bcn_msg.data)

                elif bcn_msg.hdr.bcn_type == assembler.data_piece_bcn_type:
                    assembler.data_piece += bytearray(bcn_msg.data)

                    # check if now data is full
                    if assembler.length() == assembler.full_data_len:
                        # now assemble data
                        assembler.assemble_message(assembler.data_piece)

                        # print assembled data and reset buffer
                        assembler.display_assembled_msg()
                        assembler.reset_buffer()
                    else:
                        pass
                else:
                    assembler.reset_buffer()
            else:
                break

        return msg_count_in_frame > 0

    def time_to_us(ts1: datetime.time, ts2: datetime.time):
        milliseconds_diff = (ts1.microsecond / 1000) + (
            ts1.hour * 3600 + ts1.minute * 60 + ts1.second
        ) * 1000
        milliseconds_diff -= (ts2.microsecond / 1000) + (
            ts2.hour * 3600 + ts2.minute * 60 + ts2.second
        ) * 1000

        return datetime.timedelta(milliseconds=milliseconds_diff)

    def get_delta_from_frame(self, bcn_frame: "BeaconFrame"):
        return BeaconFrame.time_to_us(self.timestamp, bcn_frame.timestamp)

    def display_frame(self):
        bcn_str = f"{self.timestamp} [[bold magenta]OBC[/bold magenta]] BeaconFrame> => \n"

        msg_idx = 0
        for bcn_msg in self.beacon_messages:
            bcn_str += f"\t{bcn_msg.display_beacon_message()}\n"
            msg_idx += 1
        print(bcn_str)


class BeaconSniffer:
    MAX_BCN_NUMBER = 256

    def __init__(self):
        self.beacon_frames_list: List[BeaconFrame] = []
        self.partial_frames: List[BeaconFrame] = []
        self.last_rcvd_beacon_number = 0
        self.deserializer: data_deserializer = data_deserializer()
        self.assembler = MessageAssembler(self.deserializer)

    def parse_beacon_frame(self, timestamp: datetime.time, frame_data: bytes) -> bool:
        bcn_frm = BeaconFrame(self.deserializer)

        parse_result = bcn_frm.parse_beacon_frame(
            timestamp, frame_data, self.assembler)

        if parse_result:
            if len(self.beacon_frames_list) > 0:
                print(
                    f":down_arrow: {bcn_frm.get_delta_from_frame(self.beacon_frames_list[-1])} :down_arrow: "
                )

            self.beacon_frames_list.append(bcn_frm)

            if bcn_frm.is_split_frame:
                self.partial_frames.append(bcn_frm)

            # if (
            #     (self.last_rcvd_beacon_number + 1) % BeaconSniffer.MAX_BCN_NUMBER
            # ) != bcn_frm.hdr.bcn_number:
            #     print(
            #         "\n...\n:exclamation_mark: [bold red]dropped frames[/bold red]\n...\n"
            #     )

            # Call to BeaconFrame.__str__()
            bcn_frm.display_frame()

            self.last_rcvd_beacon_number = bcn_frm.hdr.bcn_number

        return parse_result


class KISSParser:
    def parse(self, data: bytes) -> bool:
        """Parses a KISS frame with OBC DataCache configuration, considering UHF and OBC beacons.
        Returns if the frame is valid or not.

        Args:
            data (bytes): KISS frame in bytes format

        Returns:
            bool: whether the frame is valid or not
        """
        self.obc_parser = BeaconSniffer()
        self.frame_parser = frame_parser(self.obc_parser)
        return self.frame_parser.parse_frame(data, self.obc_parser)


def parse_timestamp(ts: str) -> "datetime.time":
    timestamp = datetime.time.fromisoformat(ts)
    return timestamp


def parse_arguments():
    parser = argparse.ArgumentParser(description="beacon sniffer")
    parser.add_argument(
        "-b",
        "--base64",
        help="Base64 encoded ",
        type=str,
        nargs="+",
        default="",
    )
    parser.add_argument(
        "-x",
        "--hex",
        help="Hex encoded ",
        type=str,
        nargs="+",
        default="",
    )
    return parser.parse_args()


def main(args):
    VERSION_STRING = "1.4.0"

    # print(f"\n-------------------------- --------------- --------------------------")
    # kwargs = vars(args)
    # print(" ---   Version --- ")
    # print(f"[bold red]   Beacon Sniffer - Simplified {VERSION_STRING}[/bold red]")
    # print(f"\n-------------------------- --------------- --------------------------")
    # print(" ---   Arguments --- ")
    # for param, val in kwargs.items():
    #     print(f"   {param.ljust(30)} = {val}")
    # print(f"\n-------------------------- --------------- --------------------------")

    # print("Detected CLI mode, parsing the base64 argument...")
    try:
        bytes_beacon: bytes = []
        if args.base64 != "":
            bytes_beacon = binascii.a2b_base64(str(args.base64))
        elif args.hex != "":
            bytes_beacon = bytes.fromhex(str(args.hex[0]))
        else:
            raise Exception("no arguments provided..")

        if len(bytes_beacon) == 0:
            raise Exception("empty or invalid beacon string")
        # print(f"Decoded base64 in hex: {binascii.hexlify(bytes_beacon)}")

        parser = KISSParser()
        parser.parse(bytes_beacon)
        print(
            f"\n-------------------------------------------------------------------"
        )

        # print(f"[bold green]Beacon frame parsing successful![/bold green]")
    except Exception as e:
        # print(f"[bold red]Beacon frame parsing failed![/bold red]")
        # print(f"Exception: {e}")
        pass


if __name__ == "__main__":
    args = parse_arguments()
    main(args)
