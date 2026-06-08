import sigrokdecode as srd

class Decoder(srd.Decoder):
    api_version = 3
    id = 'pt2240'
    name = 'PT2240'
    longname = 'PT2240 RF Decoder'
    desc = 'Decodes PT2240P ASK/OOK wireless remote control signals.'
    license = 'gplv3+'
    inputs = ['logic']
    outputs = []
    tags = ['RF']
    
    annotations = (
        ('sync', 'Sync Preamble'),
        ('bit', 'Bit'),
        ('packet', 'Decoded Packet'),
    )
    
    channels = (
        {'id': 'data', 'name': 'Data', 'desc': 'RF Demodulated Data'},
    )

    def __init__(self):
        self.samplerate = None
        self.reset()

    def reset(self):
        self.edge_sample = 0
        self.state = 'FIND_SYNC'
        self.bits = []
        self.packet_start_sample = None

    def start(self):
        self.out_ann = self.register(srd.OUTPUT_ANN)

    def metadata(self, key, value):
        if key == srd.SRD_CONF_SAMPLERATE:
            self.samplerate = value

    def decode(self):
        if not self.samplerate:
            return

        while True:
            pins = self.wait({0: 'e'})
            current_sample = self.samplenum
            
            duration = (current_sample - self.edge_sample) / float(self.samplerate)
            pin_state = pins[0]
            
            if self.state == 'FIND_SYNC':
                if pin_state == 1 and 0.011 <= duration <= 0.014:
                    self.put(self.edge_sample - int(0.0004 * self.samplerate), current_sample, self.out_ann, [0, ['SYNC', 'S']])
                    self.state = 'READ_BITS'
                    self.bits = []
                    self.packet_start_sample = current_sample
                
            elif self.state == 'READ_BITS':
                if pin_state == 0: 
                    if 0.0009 <= duration <= 0.0015:
                        self.bits.append((1, self.edge_sample, current_sample))
                    elif 0.0002 <= duration <= 0.0006:
                        self.bits.append((0, self.edge_sample, current_sample))
                    else:
                        self.state = 'FIND_SYNC'
                        
                if len(self.bits) == 24 and pin_state == 1:
                    for b_val, start, end in self.bits:
                        self.put(start, current_sample, self.out_ann, [1, [str(b_val)]])
                    
                    bit_str = ""
                    for bit_tuple in self.bits:
                        bit_str += str(bit_tuple[0])
                        
                    val = int(bit_str, 2)
                    address = val >> 4
                    data_pins = val & 0x0F
                    
                    packet_desc = "ID: 0x%05X | Data: 0x%X" % (address, data_pins)
                    self.put(self.packet_start_sample, current_sample, self.out_ann, [2, [packet_desc]])
                    
                    self.state = 'FIND_SYNC'
            
            self.edge_sample = current_sample