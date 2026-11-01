// Hama Midi codes/names follow Hama's official chart; HEX swatches are screen approximations.
export type BeadColor = { code: string; name: string; hex: string }
const hamaMidiRows: Array<[string, string, string]> = [
  ['01','White','#F6F5ED'],['02','Cream','#F4E7A6'],['03','Yellow','#F2D51E'],['04','Orange','#E97924'],['05','Red','#D83A36'],['06','Pink','#E96F91'],['07','Purple','#74519B'],['08','Blue','#205BA8'],['09','Light blue','#50A9D0'],['10','Green','#378B4C'],['11','Light green','#70B455'],['12','Brown','#684535'],['17','Grey','#777B7D'],['18','Black','#202124'],['20','Reddish brown','#8A4D39'],['21','Light brown','#A36E48'],['22','Dark red','#982F35'],['26','Blush','#D99A8D'],['27','Beige','#D2B58C'],['28','Dark green','#295F43'],['29','Claret','#A73D67'],['30','Burgundy','#6E3245'],['31','Turquoise','#159B9B'],['43','Pastel yellow','#F7E37B'],['44','Pastel red','#EE776E'],['45','Pastel purple','#A88BC1'],['46','Pastel blue','#8CC7DE'],['47','Pastel green','#9ECB86'],['48','Pastel pink','#F0A8B9'],['49','Azure','#3BAFC0'],['60','Teddybear brown','#A66B45'],['70','Light grey','#C7C9C7'],['71','Dark grey','#4D5154'],['78','Light blush','#F0BE9B'],['79','Apricot','#E89A68'],['83','Petrol blue','#27747D'],
]

export const hamaMidi: BeadColor[] = hamaMidiRows.map(([code, name, hex]) => ({ code, name, hex }))
