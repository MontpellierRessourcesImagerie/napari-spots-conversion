var reference_channel = 1;
var input_folder      = "/home/clement/Documents/projects/y2/20250505_WT-18794";
var output_folder     = "/home/clement/Documents/projects/y2/20250505_WT-18794/results";
var extension         = ".tif";
var reference_pos     = 0.5;
var subtract_bg       = false;


function join(a, b) {
	if (a.endsWith(File.separator)) { return a + b; }
	return a + File.separator + b;
}


function askSettings() {
	Dialog.create("Batch registration");
	
	Dialog.addNumber("Reference channel", 1);
	Dialog.addSlider("Reference position", 0, 100, 50);
	Dialog.addDirectory("Input folder", "");
	Dialog.addDirectory("Output folder", "");
	Dialog.addString("Extension", ".tif");
	Dialog.addCheckbox("Subtract background?", false);
	
	Dialog.show();
	
	reference_channel = Dialog.getNumber();
	reference_pos = Dialog.getNumber() / 100.0;
	input_folder = Dialog.getString();
	output_folder = Dialog.getString();
	extensions = Dialog.getString();
	subtract_bg = Dialog.getCheckbox();
	
	if (input_folder == output_folder) {
		output_folder = join(output_folder, "registered");
	}
}


function getFilesList(folder_path) {
	items = newArray();
	next_rank = 0;
	filelist = getFileList(folder_path);
	
	for (i = 0; i < lengthOf(filelist); i++) {
	    current = filelist[i];
	    full_path = join(folder_path, current);
	    
	    if (current.startsWith("."))      { continue; }
	    if (File.isDirectory(full_path))  { continue; }
	    if (!current.endsWith(extension)) { continue; }
	    
	    items[next_rank] = current;
	    next_rank++;
	}
	
	return items;
}


function registerMainChannel(im_id) {
	run("Duplicate...", "duplicate channels=" + reference_channel + "-" + reference_channel);
	name = "c_main";
	rename(name);
	IJ.log("    Processing the transformation matrices...");
	getDimensions(width, height, channels, slices, frames);
	target_frame = Math.floor(reference_pos * frames) + 1;
	target_frame = minOf(target_frame, frames);
	Stack.setFrame(target_frame);
	matrix_path = join(output_folder, "matrix.txt");
	run("MultiStackReg", "stack_1=["+name+"] action_1=Align file_1="+matrix_path+" stack_2=None action_2=Ignore file_2=[] transformation=[Rigid Body] save");
	close(name);
}


function registerAllChannels(im_id) {
	getDimensions(width, height, channels, slices, frames);
	buffer = "";
	matrix_path = join(output_folder, "matrix.txt");
	
	for (c = 1 ; c <= channels ; c++) {
		selectImage(im_id);
		run("Duplicate...", "duplicate channels=" + c + "-" + c);
		if (subtract_bg) {
			IJ.log("    Subtracting background for C" + toString(c) + "...");
			run("Subtract Background...", "rolling=50 sliding stack");
		}
		IJ.log("    Registering C" + toString(c) + "...");
		current_name = "c" + toString(c);;
		rename(current_name);
		run("MultiStackReg", "stack_1=["+current_name+"] action_1=[Load Transformation File] file_1=["+matrix_path+"] stack_2=None action_2=Ignore file_2=[] transformation=[Rigid Body]");
		entry = current_name + "=" + current_name;
		buffer += entry + " ";
	}
	
	args = buffer + "create";
	run("Merge Channels...", args);
	args = File.delete(matrix_path);
}


function main() {
	run("Close All");
	askSettings();
	filesList = getFilesList(input_folder);
	setBatchMode("hide");
	
	for (i = 0 ; i < filesList.length ; i++) {
		current = filesList[i];
		input_path = join(input_folder, current);
		output_path = join(output_folder, current);
		
		IJ.log("[" + IJ.pad(i+1, 2) + "/" + IJ.pad(filesList.length, 2) + "]. " + current);
		
		open(input_path);
		im_id = getImageID();
		registerMainChannel(im_id);
		registerAllChannels(im_id);
		saveAs("TIFF", output_path);
		run("Close All");
	}
	
	setBatchMode("exit and display");
	IJ.log("DONE.");
}


main();






