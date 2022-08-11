import groovy.time.*

// Create a log file inside the results directory to store information, for each processed image, of the time took to generate tiles.
File logfile = new File('/bioinfo_archive/AI/UTUC_Erlangen_Marburg/qupathProjUTER_server_test/results', 'logfile.log')

def timeStart = new Date()

def ImageData = QPEx.getCurrentImageData()
def server = ImageData.getServer()

server = getCurrentImageData().getServer()

// The exact relationship between magnification and pixel size is highly scanner-dependent. 
// Images scanned at 40X magnification will have a pixel size of 0.25 micrometers, and images scanned at 20X magnification will have a pixel size of 0.50 micrometers
pixelfactor = server.getPixelCalibration().getPixelHeightMicrons()

// Tiles of the dimension of 512x512 pixels will be generated
tile_px = 512
tile_mic = tile_px * pixelfactor

selectAnnotations()
// If needed, we can directly merge the annotations on the fly withouth doing it manually for each WSI
// mergeSelectedAnnotations()

// Run the tiles generator plugin
runPlugin('qupath.lib.algorithms.TilerPlugin', '{"tileSizeMicrons": '+tile_mic+',  "trimToROI": false,  "makeAnnotations": true,  "removeParentAnnotation": false}')


// Define output path (here, relative to project)
def name = GeneralTools.getNameWithoutExtension(ImageData.getServer().getMetadata().getName())
// Slide names will be slightly modified with the aim of removing any white spaces that could eventually cause issues when addressing WSI file path.
name_n = name.replaceAll("\\s","")

// The file path were to store the generated tiles will be dinamically created basing on the user.
def pathOutput = buildFilePath('/bioinfo_archive/AI/UTUC_Erlangen_Marburg/qupathProjUTER_server_test/tiles', name_n)
mkdirs(pathOutput)


i = 1

for (annotation in getAnnotationObjects()) {

    roi = annotation.getROI()
    
    def request = RegionRequest.createInstance(ImageData.getServerPath(),
    1, roi)

    // This would be useful in case we would also need to export the class of the annotated region. In this case, tiles generated from that specif annotated region will inherite its class. 
    String tiletype = annotation.getParent().getPathClass()
    
    x = roi.getCentroidX()
    y = roi.getCentroidY()

    if (!tiletype.equals("Image")) {
    
    String tilename = String.format("%s_("+x+"_"+y+")_%d.jpg", name_n, i)
    
    ImageWriterTools.writeImageRegion(server, request, pathOutput + "/" + tilename);
    
    i++
    
   }
  }

def timeStop = new Date()
TimeDuration duration = TimeCategory.minus(timeStop, timeStart)
println duration

logfile.append("Tiles generation for " + name + " took " + duration + "\n")