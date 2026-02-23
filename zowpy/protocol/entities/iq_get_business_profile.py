"""
Update Business Profile IQ - Atualização de perfil business (w:biz).

Equivalente ao UpdateBusinessProfile do go-whatsapp:
- xmlns: w:biz, type: set, to: s.whatsapp.net
- Filho <business_profile v="3" mutation_type="delta"> com um filho <address|description|email|website> com conteúdo infoData.
"""

from typing import Optional

from .iq import IqProtocolEntity
from ...protocol.structs import ProtocolNode
from ...utils.constants import YowConstants



class GetBusinessProfileIqProtocolEntity(IqProtocolEntity):
    """
    IQ para obter o perfil business.

    Estrutura (go-whatsapp):
    <iq xmlns="w:biz" type="get" to="s.whatsapp.net">
      <business_profile v="244">
        <profile jid="jid"></profile>
      </business_profile>
    </iq>
    """

    """
    IQ Response:
    ProtocolNode(tag='iq', attributes={'from': 's.whatsapp.net', 'type': 'result', 'id': '6BF4A0A0FD5571873B26D3C429CE819E'}, 
                children=[ProtocolNode(tag='business_profile', attributes={},
                children=[ProtocolNode(tag='profile', attributes={'jid': '559885700260@s.whatsapp.net', 'tag': '1098428578'}, 
                children=[ProtocolNode(tag='address', attributes={}, children=[], data=b'Presidente Sarney - State of Maranh\xc3\xa3o, Brazil'), 
                ProtocolNode(tag='description', attributes={}, children=[], data=b'We are a software development company specializing in custom-built solutions designed to drive innovation, efficiency, and business growth. From concept to deployment, we cover the entire development lifecycle with a focus on quality, scalability, and user-centered design. Our team is dedicated to transforming ideas into reliable, high-performance software tailored to meet the unique needs of each client.'), ProtocolNode(tag='email', attributes={}, children=[], data=b'hyperducktech@gmail.com'), 
                ProtocolNode(tag='latitude', attributes={}, children=[], data=b'-2.5932'), ProtocolNode(tag='longitude', attributes={}, children=[], data=b'-45.3645'), 
                ProtocolNode(tag='business_hours', 
                            attributes={'timezone': 'America/Sao_Paulo'}, children=[ProtocolNode(tag='business_hours_config', 
                            attributes={'day_of_week': 'mon', 'mode': 'specific_hours', 'open_time': '540', 'close_time': '1080'}, 
                            children=[], data=None), ProtocolNode(tag='business_hours_config', 
                            attributes={'day_of_week': 'tue', 'mode': 'specific_hours', 'open_time': '540', 'close_time': '1080'},
                            children=[], data=None), ProtocolNode(tag='business_hours_config', attributes={'day_of_week': 'wed', 'mode': 'specific_hours', 'open_time': '540', 'close_time': '1080'}, children=[], data=None), 
                            ProtocolNode(tag='business_hours_config', attributes={'day_of_week': 'thu', 'mode': 'specific_hours', 'open_time': '540', 'close_time': '1080'}, children=[], data=None), 
                            ProtocolNode(tag='business_hours_config', attributes={'day_of_week': 'fri', 'mode': 'specific_hours', 'open_time': '540', 'close_time': '1080'}, children=[], data=None)], data=None), 
                            ProtocolNode(tag='categories', attributes={}, children=[ProtocolNode(tag='category', 
                            attributes={'id': '1130035050388269'}, children=[], data=b'\xd8\xb4\xd8\xb1\xd9\x83\xd8\xa9 \xd8\xaa\xd8\xb9\xd9\x85\xd9\x84 \xd9\x81\xd9\x8a \xd9\x85\xd8\xac\xd8\xa7\xd9\x84 \xd8\xaa\xd9\x83\xd9\x86\xd9\x88\xd9\x84\xd9\x88\xd8\xac\xd9\x8a\xd8\xa7 \xd8\xa7\xd9\x84\xd9\x85\xd8\xb9\xd9\x84\xd9\x88\xd9\x85\xd8\xa7\xd8\xaa'), ProtocolNode(tag='category', attributes={'id': '2211'}, children=[], data=b'\xd8\xa8\xd8\xb1\xd8\xa7\xd9\x85\xd8\xac')], data=None), 
                            ProtocolNode(tag='profile_options', attributes={}, children=[ProtocolNode(tag='commerce_experience', attributes={}, children=[], data=b'none'), 
                            ProtocolNode(tag='cart_enabled', attributes={}, children=[], data=b'true'), 
                            ProtocolNode(tag='direct_connection', attributes={}, children=[], data=b'false'), 
                            ProtocolNode(tag='is_responsive', attributes={}, children=[], data=b'false'), 
                            ProtocolNode(tag='bot_fields', attributes={}, children=[ProtocolNode(tag='is_typing_indicator_enabled', attributes={}, children=[], data=b'false')], data=None)], data=None), 
                            ProtocolNode(tag='cover_photo', attributes={'id': '1226199302844514'}, children=[], data=b'https://media-atl3-3.cdn.whatsapp.net/v/t61.43035-24/491845046_1663475664533686_7771715480608891132_n.jpg?ccb=1-7&_nc_sid=1937c6&_nc_ohc=MjI64IIrXjQQ7kNvwEy5Dot&_nc_oc=Adk3tHUitUf8ji07vKlY3HWNX3T_U0w5oNQ0XJhI53D3sG7K1379bhcyWgRItDHrzZPuYaU_vbu5g-fruRaE1sPB&_nc_ad=z-m&_nc_cid=0&_nc_zt=3&_nc_ht=media-atl3-3.cdn.whatsapp.net&_nc_gid=DVM8f0yrcUg49aZVCfXuXg&oh=01_Q5Aa3wGDFbxADKP3DdtEkzKnGXr1x_yiwwy5NnknPgnhi-lHFQ&oe=69C2E87D'), 
                            ProtocolNode(tag='direct_connection', attributes={'enabled': 'false'}, children=[ProtocolNode(tag='features', attributes={'name': 'default'}, children=[], data=None)], data=None), ProtocolNode(tag='member_since_text', attributes={}, children=[], data=b'\xd8\xaa\xd9\x85 \xd8\xa7\xd9\x84\xd8\xa7\xd9\x86\xd8\xb6\xd9\x85\xd8\xa7\xd9\x85 \xd9\x81\xd9\x8a \xe2\x80\x8f\xd9\x85\xd8\xa7\xd9\x8a\xd9\x88, \xd9\xa2\xd9\xa0\xd9\xa2\xd9\xa5\xe2\x80\x8f'), ProtocolNode(tag='offerings', attributes={}, children=[ProtocolNode(tag='category', attributes={'id': '1896171907331974', 'name': 'Ø®Ù\x8aØ§Ø±Ø§Øª Ø§Ù\x84Ø¯Ù\x81Ø¹ Ù\x88Ø§Ù\x84Ø§Ù\x86ØªØ¸Ø§Ø±'}, 
                            children=[ProtocolNode(tag='offering', attributes={'id': 'business_pix_accepted', 'is_offered': 'true'}, children=[], data=b'\xd9\x86\xd9\x82\xd8\xa8\xd9\x84 Pix')], data=None)], data=None), 
                            ProtocolNode(tag='automated_type', attributes={}, children=[], data=b'unknown'), ProtocolNode(tag='biz_identity_info', attributes={'phone_number': '', 'type': 'smb', 'display_name': 'Hyper Duck', 'vlevel': 'unknown', 'serial': '4497206798683073789', 'is_signed': 'true', 'revoked': 'false', 'actual_actors': 'self', 'host_storage': 'on_premise'}, children=[], data=None), ProtocolNode(tag='member_since_ts', attributes={}, children=[], data=b'1746628277')], data=None)], data=None)], data=None), message='Perfil business obtido', error_message=None, errors=[], error_code=None, error_codes=[], reason=None)
    
        <iq from="s.whatsapp.net" type="result" id="6BF4A0A0FD5571873B26D3C429CE819E">
        <business_profile>
            <profile jid="559885700260@s.whatsapp.net" tag="1098428578">
            <address>
                0x507265736964656e7465205361726e6579202d205374617465206f66204d6172616e68c3a36f2c204272617a696c
            </address>
            <description>
                0x576520617265206120736f66747761726520646576656c6f706d656e7420636f6d70616e79207370656369616c697a696e6720696e20637573746f6d2d6275696c7420736f6c7574696f6e732064657369676e656420746f20647269766520696e6e6f766174696f6e2c20656666696369656e63792c20616e6420627573696e6573732067726f7774682e2046726f6d20636f6e6365707420746f206465706c6f796d656e742c20776520636f7665722074686520656e7469726520646576656c6f706d656e74206c6966656379636c652077697468206120666f637573206f6e207175616c6974792c207363616c6162696c6974792c20616e6420757365722d63656e74657265642064657369676e2e204f7572207465616d2069732064656469636174656420746f207472616e73666f726d696e6720696465617320696e746f2072656c6961626c652c20686967682d706572666f726d616e636520736f667477617265207461696c6f72656420746f206d6565742074686520756e69717565206e65656473206f66206561636820636c69656e742e
            </description>
            <email>
                0x68797065726475636b7465636840676d61696c2e636f6d
            </email>
            <latitude>
                0x2d322e35393332
            </latitude>
            <longitude>
                0x2d34352e33363435
            </longitude>
            <business_hours timezone="America/Sao_Paulo">
                <business_hours_config day_of_week="mon" mode="specific_hours" open_time="540" close_time="1080" />
                <business_hours_config day_of_week="tue" mode="specific_hours" open_time="540" close_time="1080" />
                <business_hours_config day_of_week="wed" mode="specific_hours" open_time="540" close_time="1080" />
                <business_hours_config day_of_week="thu" mode="specific_hours" open_time="540" close_time="1080" />
                <business_hours_config day_of_week="fri" mode="specific_hours" open_time="540" close_time="1080" />
            </business_hours>
            <categories>
                <category id="1130035050388269">
                0xd8b4d8b1d983d8a920d8aad8b9d985d98420d981d98a20d985d8acd8a7d98420d8aad983d986d988d984d988d8acd98ad8a720d8a7d984d985d8b9d984d988d985d8a7d8aa
                </category>
                <category id="2211">
                0xd8a8d8b1d8a7d985d8ac
                </category>
            </categories>
            <profile_options>
                <commerce_experience>
                0x6e6f6e65
                </commerce_experience>
                <cart_enabled>
                0x74727565
                </cart_enabled>
                <direct_connection>
                0x66616c7365
                </direct_connection>
                <is_responsive>
                0x66616c7365
                </is_responsive>
                <bot_fields>
                <is_typing_indicator_enabled>
                    0x66616c7365
                </is_typing_indicator_enabled>
                </bot_fields>
            </profile_options>
            <cover_photo id="1226199302844514">
                0x68747470733a2f2f6d656469612d61746c332d332e63646e2e77686174736170702e6e65742f762f7436312e34333033352d32342f3439313834353034365f313636333437353636343533333638365f373737313731353438303630383839313133325f6e2e6a70673f6363623d312d37265f6e635f7369643d313933376336265f6e635f6f68633d4d6a493634494972586a5151376b4e7677457935446f74265f6e635f6f633d41646b3374485569745566386a693037764b6c593348574e5833545f553077356f4e5130584a6849353344337347374b313337396268637957675249744448727a5a50755961555f76627535672d66727552614531735042265f6e635f61643d7a2d6d265f6e635f6369643d30265f6e635f7a743d33265f6e635f68743d6d656469612d61746c332d332e63646e2e77686174736170702e6e6574265f6e635f6769643d44564d38663079726355673439615a56436658755867266f683d30315f513541613377474446627841444b5033446474456b7a4b6e47587231785f7969777779354e6e6b6e50676e68692d6c484651266f653d3639433245383744
            </cover_photo>
            <direct_connection enabled="false">
                <features name="default" />
            </direct_connection>
            <member_since_text>
                0xd8aad98520d8a7d984d8a7d986d8b6d985d8a7d98520d981d98a20e2808fd985d8a7d98ad9882c20d9a2d9a0d9a2d9a5e2808f
            </member_since_text>
            <offerings>
                <category id="1896171907331974" name="Ø®ÙØ§Ø±Ø§Øª Ø§ÙØ¯ÙØ¹ ÙØ§ÙØ§ÙØªØ¸Ø§Ø±">
                <offering id="business_pix_accepted" is_offered="true">
                    0xd986d982d8a8d98420506978
                </offering>
                </category>
            </offerings>
            <automated_type>
                0x756e6b6e6f776e
            </automated_type>
            <biz_identity_info phone_number="" type="smb" display_name="Hyper Duck" vlevel="unknown" serial="4497206798683073789" is_signed="true" revoked="false" actual_actors="self" host_storage="on_premise" />
            <member_since_ts>
                0x31373436363238323737
            </member_since_ts>
            </profile>
        </business_profile>
        </iq>
    """

    def __init__(
        self,
        iq_id: Optional[str] = None,
        jid: Optional[str] = None,
    ):
        """
        Args:
            info_type: Um de "address", "description", "email", "website".
            info_data: Conteúdo do campo (texto).
            iq_id: ID do IQ (gerado se None).

        Raises:
            InvalidBusinessUpdateInfoType: Se info_type não for permitido.
        """
       
        super().__init__(
            xmlns="w:biz",
            iq_type="get",
            iq_id=iq_id,
            to=YowConstants.WHATSAPP_SERVER,
        )
        self.jid = jid
    def to_protocol_node(self) -> ProtocolNode:
        node = super().to_protocol_node()
        profile = ProtocolNode(
            tag="profile",
            attributes={"jid": self.jid},
        )
        business_profile = ProtocolNode(
            tag="business_profile",
            attributes={"v": "244"},
            children=[profile],
        )
        node.children.append(business_profile)
        return node


    @staticmethod
    def from_protocol_node(node: ProtocolNode) -> "GetBusinessProfileIqProtocolEntity":
        entity = GetBusinessProfileIqProtocolEntity()
        entity.iq_id = node.get_attribute("id")
        entity.jid = node.get_child("profile").get_attribute("jid")
        entity.iq_type = node.get_attribute("type")
        entity.to = node.get_attribute("to")
        entity.xmlns = node.get_attribute("xmlns")
        entity.from_jid = node.get_attribute("from")
        entity.to_jid = node.get_attribute("to")
        entity.id = node.get_attribute("id")
        return entity

